"""
paper_trader.py — paper-trading runner for the dual-mode trading bot.

Two broker backends:

1. LocalSimBroker (default) — streams simulated minute bars and fills orders
   with slippage. Works everywhere, including sandboxed environments with no
   market access. Use it to verify the live decision loop end-to-end:
       python3 paper_trader.py --demo --sessions 5

2. AlpacaPaperBroker — Alpaca's PAPER endpoint (no real money). Requires your
   own account and API keys (https://alpaca.markets, free), and an
   unrestricted network. NEVER put live-account keys here.
       export ALPACA_API_KEY=...  ALPACA_API_SECRET=...
       python3 paper_trader.py --broker alpaca --symbol VXX

The trading loop is identical for both backends: pull latest bars ->
regenerate signals on the rolling window -> submit orders -> manage
stop/target/time exits -> journal every decision to paper_trades.csv.

⚠️ This is a PAPER trading harness. It does not, and must not, place real
orders. Validate for months on paper before any live deployment decision.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from trading_bot import TradingBot, TradingMode, AssetClass, VolParams, RiskConfig
import backtest_engine as be

# Final walk-forward-validated configuration of the one book that passed all
# targets out-of-sample (see PERFORMANCE_REPORT.md — VXX-SCALP-MR):
VALIDATED_VXX_PARAMS = VolParams(z_window=585, z_entry_short=1.8,
                                 z_entry_long=-2.0, z_exit=0.6,
                                 sl_atr=1.5, max_hold=60)


# ----------------------------------------------------------------------------
# Broker interface
# ----------------------------------------------------------------------------

@dataclass
class Fill:
    ts: str
    side: str          # "buy" | "sell"
    qty: float
    price: float


class LocalSimBroker:
    """Simulated market + instant fills with slippage. No network needed."""

    def __init__(self, seed: int = 777, sessions: int = 5,
                 slippage_bps: float = 1.0):
        # generate `sessions` days the optimizer has never seen
        self.df = be.simulate_vxx_minute(sessions + 3, seed=seed)
        self.cursor = 390 * 2          # warm-up history for indicators
        self.slip = slippage_bps / 1e4
        self.position = 0.0
        self.cash = 100_000.0

    # -- market data ---------------------------------------------------------
    def get_bars(self, symbol: str, lookback: int) -> pd.DataFrame:
        start = max(0, self.cursor - lookback)
        return self.df.iloc[start:self.cursor]

    def next_bar(self) -> bool:
        self.cursor += 1
        return self.cursor < len(self.df)

    def last_price(self) -> float:
        return float(self.df["close"].iloc[self.cursor - 1])

    def now(self) -> str:
        return str(self.df.index[self.cursor - 1])

    # -- account / orders ----------------------------------------------------
    def submit_order(self, symbol: str, side: str, qty: float) -> Fill:
        px = self.last_price() * (1 + self.slip * (1 if side == "buy" else -1))
        signed = qty if side == "buy" else -qty
        self.position += signed
        self.cash -= signed * px
        return Fill(self.now(), side, qty, px)

    def equity(self) -> float:
        return self.cash + self.position * self.last_price()


class AlpacaPaperBroker:
    """Minimal REST adapter for Alpaca's PAPER endpoint (paper-api.alpaca.markets).

    Hard-wired to the paper URL — it cannot touch a live account. Requires
    ALPACA_API_KEY / ALPACA_API_SECRET env vars and network access to
    alpaca.markets (blocked in sandboxed CI environments)."""

    TRADE_URL = "https://paper-api.alpaca.markets"
    DATA_URL = "https://data.alpaca.markets"

    def __init__(self):
        import requests
        self.rq = requests
        key, sec = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_API_SECRET")
        if not key or not sec:
            raise SystemExit("Set ALPACA_API_KEY and ALPACA_API_SECRET "
                             "(paper keys from https://app.alpaca.markets).")
        self.h = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}
        acct = self._get(f"{self.TRADE_URL}/v2/account")
        print(f"[alpaca] connected — paper account {acct['account_number']}, "
              f"equity ${float(acct['equity']):,.0f}")

    def _get(self, url, **params):
        r = self.rq.get(url, headers=self.h, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def get_bars(self, symbol: str, lookback: int) -> pd.DataFrame:
        js = self._get(f"{self.DATA_URL}/v2/stocks/{symbol}/bars",
                       timeframe="1Min", limit=min(lookback, 10000),
                       adjustment="raw", feed="iex")
        bars = js.get("bars", [])
        if not bars:
            return pd.DataFrame()
        df = pd.DataFrame(bars).rename(columns={
            "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df.index = pd.to_datetime(df.pop("t"))
        return df[["open", "high", "low", "close", "volume"]].astype(float)

    def submit_order(self, symbol: str, side: str, qty: float) -> Fill:
        r = self.rq.post(f"{self.TRADE_URL}/v2/orders", headers=self.h,
                         json={"symbol": symbol, "side": side,
                               "qty": str(round(qty, 4)), "type": "market",
                               "time_in_force": "day"}, timeout=15)
        r.raise_for_status()
        o = r.json()
        return Fill(o["submitted_at"], side, qty,
                    float(o.get("filled_avg_price") or 0.0))

    def equity(self) -> float:
        return float(self._get(f"{self.TRADE_URL}/v2/account")["equity"])


# ----------------------------------------------------------------------------
# Paper trading loop
# ----------------------------------------------------------------------------

class PaperTrader:
    def __init__(self, broker, symbol: str = "VXX",
                 journal_path: str = "paper_trades.csv"):
        self.broker = broker
        self.symbol = symbol
        self.bot = TradingBot(TradingMode.ULTRA_PRECISION_SCALPER,
                              AssetClass.VOLATILITY,
                              vol_params=VALIDATED_VXX_PARAMS,
                              risk=RiskConfig(use_kelly=False))
        self.lookback = VALIDATED_VXX_PARAMS.z_window + 200
        self.pos = 0            # -1 / 0 / +1
        self.qty = 0.0
        self.entry_px = self.stop = 0.0
        self.bars_held = 0
        self.max_hold = 0
        self.journal_path = journal_path
        self._init_journal()

    def _init_journal(self):
        if not os.path.exists(self.journal_path):
            with open(self.journal_path, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["ts", "event", "side", "qty", "price", "equity", "note"])

    def _log(self, ts, event, side="", qty="", price="", note=""):
        with open(self.journal_path, "a", newline="") as f:
            csv.writer(f).writerow([ts, event, side, qty, price,
                                    f"{self.broker.equity():.2f}", note])

    def on_bar(self):
        df = self.broker.get_bars(self.symbol, self.lookback)
        if len(df) < self.lookback // 2:
            return
        sig = self.bot.generate_signals(df)
        last = sig.iloc[-1]
        px = float(df["close"].iloc[-1])
        ts = str(df.index[-1])

        if self.pos != 0:
            self.bars_held += 1
            hit_stop = (self.pos == 1 and px <= self.stop) or \
                       (self.pos == -1 and px >= self.stop)
            timed_out = self.max_hold > 0 and self.bars_held >= self.max_hold
            if hit_stop or timed_out or last["force_flat"]:
                side = "sell" if self.pos == 1 else "buy"
                fill = self.broker.submit_order(self.symbol, side, self.qty)
                pnl = (fill.price - self.entry_px) * self.qty * self.pos
                reason = ("stop" if hit_stop else
                          "time" if timed_out else "mean_touch")
                self._log(ts, "EXIT", side, self.qty, f"{fill.price:.4f}",
                          f"{reason} pnl={pnl:+.2f}")
                self.pos, self.qty = 0, 0.0
                return

        if self.pos == 0 and (last["long_entry"] or last["short_entry"]):
            direction = 1 if last["long_entry"] else -1
            risk_amt = self.broker.equity() * self.bot.risk.risk_per_trade \
                * float(last["size_mult"])
            sl_dist = float(last["sl_dist"])
            if not np.isfinite(sl_dist) or sl_dist <= 0:
                return
            qty = round(risk_amt / sl_dist, 2)
            side = "buy" if direction == 1 else "sell"
            fill = self.broker.submit_order(self.symbol, side, qty)
            self.pos, self.qty = direction, qty
            self.entry_px = fill.price
            self.stop = fill.price - direction * sl_dist
            self.bars_held = 0
            self.max_hold = int(last["max_hold"])
            self._log(ts, "ENTRY", side, qty, f"{fill.price:.4f}",
                      f"stop={self.stop:.4f} max_hold={self.max_hold}")

    # -- runners ---------------------------------------------------------
    def run_demo(self):
        """Consume the entire simulated stream as fast as possible."""
        start_eq = self.broker.equity()
        bars = 0
        while self.broker.next_bar():
            self.on_bar()
            bars += 1
        end_eq = self.broker.equity()
        print(f"[demo] {bars:,} bars processed — equity "
              f"${start_eq:,.0f} -> ${end_eq:,.0f} "
              f"({(end_eq / start_eq - 1) * 100:+.2f}%) — journal: "
              f"{self.journal_path}")

    def run_live_paper(self, poll_seconds: int = 60):
        """Poll the broker once per bar interval. Ctrl-C to stop."""
        print(f"[paper] trading {self.symbol} — polling every {poll_seconds}s")
        while True:
            try:
                self.on_bar()
            except Exception as exc:      # keep the loop alive; log the error
                self._log(pd.Timestamp.now(), "ERROR", note=str(exc)[:200])
                print(f"[paper] error: {exc}", file=sys.stderr)
            time.sleep(poll_seconds)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--broker", choices=["sim", "alpaca"], default="sim")
    ap.add_argument("--symbol", default="VXX")
    ap.add_argument("--demo", action="store_true",
                    help="run the local simulated stream to completion")
    ap.add_argument("--sessions", type=int, default=5,
                    help="simulated sessions for --demo")
    ap.add_argument("--seed", type=int, default=777)
    args = ap.parse_args()

    if args.broker == "alpaca":
        broker = AlpacaPaperBroker()
        PaperTrader(broker, args.symbol).run_live_paper()
    else:
        broker = LocalSimBroker(seed=args.seed, sessions=args.sessions)
        PaperTrader(broker, args.symbol).run_demo()


if __name__ == "__main__":
    main()
