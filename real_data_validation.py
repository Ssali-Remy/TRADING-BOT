"""
real_data_validation.py — validate the trading bot on REAL market data.

This environment's network policy blocks every market-data endpoint (Yahoo,
Stooq, CBOE, FRED, ...), but PyPI is reachable — and several packages ship
genuine historical market data inside the wheel:

  * skfolio      -> S&P 500 index, daily closes, 1990-2022 (33 years)
  * backtesting  -> GOOG daily OHLCV 2004-2013; EURUSD hourly OHLC+tick-volume
                    2017-2018 (real intraday data)

Books tested (walk-forward 70/30, params chosen on train only):

  1. REAL-SPX-MACRO      Mode 2 macro-trend on real S&P 500 daily (1990-2022),
                         plus a dedicated 2020-2022 out-of-sample slice (the
                         most recent real window obtainable offline).
  2. REAL-GOOG-TRANSFER  The SPX-trained parameters applied to GOOG with ZERO
                         tuning — a pure cross-asset transfer test.
  3. REAL-RV-MEANREV     Volatility z-score book on the realized-volatility
                         series computed from real S&P 500 returns. Realized
                         vol is not directly tradeable — this is a logic test
                         of mean-reversion alpha on real market dynamics.
  4. REAL-EURUSD-SCALPER Mode 1 scalper at hourly grain on real EURUSD bars
                         with real tick volume.

Honesty notes:
  * S&P closes are close-only; OHLC is synthesized deterministically and
    conservatively (wicks = 15% of the bar body, no randomness), which
    slightly understates ATR — disclosed in the report.
  * No data after 2022-12 exists in any offline source; "the past 3 years"
    cannot be tested from this sandbox. 2020-2022 is the closest real window.

Run:  python3 real_data_validation.py
"""

from __future__ import annotations

import itertools
import time
from dataclasses import replace, asdict

import numpy as np
import pandas as pd

import backtest_engine as be
from backtest_engine import (
    run_backtest, compute_metrics, composite_score, meets_targets,
    monte_carlo, ascii_curve, fmt, TARGETS,
)
from trading_bot import (
    TradingBot, TradingMode, AssetClass, RiskConfig,
    ScalperParams, MacroParams, VolParams,
    markov_regime_prob, rolling_hurst,
)


# ----------------------------------------------------------------------------
# Real data loading
# ----------------------------------------------------------------------------

def ohlc_from_close(close: pd.Series) -> pd.DataFrame:
    """Deterministic, conservative OHLC synthesis for close-only series.
    open = previous close; wicks extend 15% of the body beyond it.
    No randomness -> no fabricated favorable fills."""
    o = close.shift(1).fillna(close.iloc[0])
    body_hi = pd.concat([o, close], axis=1).max(axis=1)
    body_lo = pd.concat([o, close], axis=1).min(axis=1)
    wick = 0.15 * (body_hi - body_lo)
    return pd.DataFrame({
        "open": o, "high": body_hi + wick, "low": body_lo - wick,
        "close": close, "volume": 1e9,
    }, index=close.index)


def load_spx() -> pd.DataFrame:
    from skfolio.datasets import load_sp500_index
    px = load_sp500_index()["SP500"].astype(float)
    px.index = pd.to_datetime(px.index)
    return ohlc_from_close(px)


def load_goog() -> pd.DataFrame:
    from backtesting.test import GOOG
    df = GOOG.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index)
    return df.astype(float)


def load_eurusd() -> pd.DataFrame:
    from backtesting.test import EURUSD
    df = EURUSD.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index)
    return df.astype(float)


def load_realized_vol() -> pd.DataFrame:
    """Realized-vol index (VIX physical counterpart) from real S&P returns:
    5-day rolling std of daily returns, annualized, in vol points."""
    from skfolio.datasets import load_sp500_index
    px = load_sp500_index()["SP500"].astype(float)
    px.index = pd.to_datetime(px.index)
    rv = (px.pct_change().rolling(5).std() * np.sqrt(252) * 100).dropna()
    rv = rv.clip(lower=3.0)
    return ohlc_from_close(rv)


# ----------------------------------------------------------------------------
# Evaluation helpers
# ----------------------------------------------------------------------------

def precompute_macro(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["regime_prob"] = markov_regime_prob(df["close"].pct_change())
    df["hurst"] = rolling_hurst(df["close"], MacroParams().hurst_window)
    return df


def evaluate(mode, asset, params, df, *, risk_pct, is_scalper, leverage,
             comm, slip):
    bot = TradingBot(mode, asset,
                     scalper_params=params if isinstance(params, ScalperParams) else None,
                     macro_params=params if isinstance(params, MacroParams) else None,
                     vol_params=params if isinstance(params, VolParams) else None,
                     risk=RiskConfig(risk_per_trade=risk_pct))
    sig = bot.generate_signals(df)
    return run_backtest(df, sig, bot.risk, is_scalper, max_leverage=leverage,
                        commission_bps=comm, slippage_bps=slip)


def grid_search(name, mode, asset, base, grid, train, min_tr, log, **kw):
    keys = list(grid)
    best, best_sc, best_p = None, -np.inf, base
    print(f"\n=== {name}: grid search on train "
          f"({int(np.prod([len(v) for v in grid.values()]))} configs) ===")
    log.append(f"\n### {name} — optimization log (train only)")
    for i, combo in enumerate(itertools.product(*grid.values()), 1):
        p = replace(base, **dict(zip(keys, combo)))
        res = evaluate(mode, asset, p, train, **kw)
        sc = composite_score(res.metrics, min_tr)
        line = f"  iter {i:>3} {fmt(res.metrics)}"
        print(line); log.append(line)
        if sc > best_sc:
            best, best_sc, best_p = res, sc, p
    line = f"  BEST (train): {fmt(best.metrics)}"
    print(line); log.append(line)
    return best_p, best


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main(report_path="REAL_DATA_VALIDATION.md"):
    t0 = time.time()
    log: list[str] = []
    sections = []

    hdr = "| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |"
    sep = "|---|---|---|---|---|---|---|---|"

    def row(label, m):
        return (f"| {label} | {m['n_trades']} | {m['win_rate']*100:.1f}% | "
                f"{min(m['profit_factor'],99):.2f} | {m['sharpe']:.2f} | "
                f"{m['max_drawdown']*100:.2f}% | {m['total_return']*100:.2f}% | "
                f"{m['payoff_ratio']:.2f} |")

    # ---------------- Book 1: REAL S&P 500 macro trend --------------------
    spx = load_spx()
    split = int(len(spx) * 0.70)
    train = precompute_macro(spx.iloc[:split])
    test = precompute_macro(spx.iloc[split:])
    kw = dict(risk_pct=0.02, is_scalper=False, leverage=1.5, comm=0.5, slip=1.0)
    grid = {"adx_min": [12.0, 15.0, 18.0], "regime_prob_entry": [0.55, 0.65],
            "trail_atr": [2.5, 3.5, 4.5], "breakout_lookback": [30, 55]}
    p_spx, res_tr = grid_search("REAL-SPX-MACRO (S&P 500 daily 1990-2022)",
                                TradingMode.MACRO_TREND, AssetClass.INDEX,
                                MacroParams(), grid, train, 15, log, **kw)
    res_oos = evaluate(TradingMode.MACRO_TREND, AssetClass.INDEX, p_spx, test, **kw)
    print(f"  OOS {test.index[0].date()}→{test.index[-1].date()}: {fmt(res_oos.metrics)}")
    recent = precompute_macro(spx.loc["2020":"2022"])
    res_recent = evaluate(TradingMode.MACRO_TREND, AssetClass.INDEX, p_spx, recent, **kw)
    print(f"  2020-2022 slice: {fmt(res_recent.metrics)}")
    mc = monte_carlo(res_oos.trades)
    sections.append((
        "REAL-SPX-MACRO — Mode 2 on real S&P 500 daily closes (1990-2022)",
        [row("Train 1990→2013 (optimized)", res_tr.metrics),
         row(f"**OOS {test.index[0].year}→2022 (untouched)**", res_oos.metrics),
         row("2020→2022 slice (most recent real data)", res_recent.metrics)],
        p_spx, res_oos, mc,
        "Real index closes; OHLC synthesized conservatively (close-only source). "
        "Params chosen on pre-2013 data only — everything after is out-of-sample."))

    # ---------------- Book 2: GOOG transfer test ---------------------------
    goog = precompute_macro(load_goog())
    res_goog = evaluate(TradingMode.MACRO_TREND, AssetClass.INDEX, p_spx, goog, **kw)
    print(f"\n=== REAL-GOOG-TRANSFER (zero tuning) ===\n  {fmt(res_goog.metrics)}")
    log.append(f"\n### REAL-GOOG-TRANSFER\n  {fmt(res_goog.metrics)}")
    sections.append((
        "REAL-GOOG-TRANSFER — SPX-trained params on real GOOG OHLCV (2004-2013), zero tuning",
        [row("GOOG full period (pure transfer)", res_goog.metrics)],
        p_spx, res_goog, monte_carlo(res_goog.trades),
        "Real daily OHLCV. The parameters were never shown any GOOG data — "
        "this is a cross-asset generalization test of the trend logic."))

    # ---------------- Book 3: realized-vol mean reversion ------------------
    rv = load_realized_vol()
    split = int(len(rv) * 0.70)
    rv_tr, rv_te = rv.iloc[:split], rv.iloc[split:]
    kwv = dict(risk_pct=0.015, is_scalper=False, leverage=2.0, comm=0.3, slip=1.0)
    gridv = {"z_entry_short": [1.5, 2.0], "z_window": [40, 60, 90],
             "z_exit": [0.3, 0.5], "sl_atr": [2.0, 4.0]}
    p_rv, res_rvtr = grid_search("REAL-RV-MEANREV (S&P realized vol 1990-2022)",
                                 TradingMode.MACRO_TREND, AssetClass.VOLATILITY,
                                 VolParams(), gridv, rv_tr, 25, log, **kwv)
    res_rvo = evaluate(TradingMode.MACRO_TREND, AssetClass.VOLATILITY, p_rv, rv_te, **kwv)
    print(f"  OOS {rv_te.index[0].date()}→{rv_te.index[-1].date()}: {fmt(res_rvo.metrics)}")
    rv_recent = rv.loc["2020":"2022"]
    res_rvr = evaluate(TradingMode.MACRO_TREND, AssetClass.VOLATILITY, p_rv, rv_recent, **kwv)
    print(f"  2020-2022 slice: {fmt(res_rvr.metrics)}")
    sections.append((
        "REAL-RV-MEANREV — volatility z-score book on realized vol of real S&P returns",
        [row("Train (optimized)", res_rvtr.metrics),
         row("**OOS (untouched)**", res_rvo.metrics),
         row("2020→2022 slice", res_rvr.metrics)],
        p_rv, res_rvo, monte_carlo(res_rvo.trades),
        "⚠️ Realized vol is NOT directly tradeable (no VIX futures data exists "
        "offline). This validates the mean-reversion LOGIC on real market "
        "dynamics, not an executable P&L."))

    # ---------------- Book 4: EURUSD hourly scalper -------------------------
    eu = load_eurusd()
    split = int(len(eu) * 0.70)
    eu_tr, eu_te = eu.iloc[:split], eu.iloc[split:]
    kws = dict(risk_pct=0.0075, is_scalper=True, leverage=5.0, comm=0.2, slip=0.5)
    base_s = replace(ScalperParams(), open_skip=1, close_skip=1, trend_ma=24,
                     squeeze_lookback=120, max_hold=24)
    grids = {"fade_k": [1.4, 1.8], "sl_atr": [4.0, 7.0],
             "fade_tp_frac": [0.5, 0.65], "max_hold": [24, 48]}
    p_eu, res_eutr = grid_search("REAL-EURUSD-SCALPER (hourly 2017-2018)",
                                 TradingMode.ULTRA_PRECISION_SCALPER,
                                 AssetClass.INDEX, base_s, grids, eu_tr, 25,
                                 log, **kws)
    res_euo = evaluate(TradingMode.ULTRA_PRECISION_SCALPER, AssetClass.INDEX,
                       p_eu, eu_te, **kws)
    print(f"  OOS {eu_te.index[0].date()}→{eu_te.index[-1].date()}: {fmt(res_euo.metrics)}")
    sections.append((
        "REAL-EURUSD-SCALPER — Mode 1 on real EURUSD hourly bars with real tick volume",
        [row("Train (optimized)", res_eutr.metrics),
         row("**OOS (untouched)**", res_euo.metrics)],
        p_eu, res_euo, monte_carlo(res_euo.trades),
        "Real intraday OHLC + tick volume. Hourly grain (minute data does not "
        "exist in any offline source)."))

    # ---------------- Report ------------------------------------------------
    L = ["# REAL DATA VALIDATION REPORT", ""]
    L.append(f"*Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}. All series below "
             f"are REAL market data obtained from datasets bundled inside PyPI "
             f"packages (skfolio, backtesting) — the only data source this "
             f"sandbox's network policy allows.*")
    L.append("")
    L.append("## Data constraint — read first")
    L.append("")
    L.append("**No offline source contains data after 2022-12-28**, so \"the "
             "past 3 years\" cannot be tested from this environment. The most "
             "recent real window (2020–2022, reported per book below) includes "
             "the COVID crash, the 2020-21 bull run and the 2022 bear market — "
             "a demanding out-of-sample stress test. For current data, run "
             "`backtest_engine.py` on an unrestricted network (it auto-uses "
             "yfinance).")
    L.append("")
    L.append("Targets: WR ≥ 85%, PF ≥ 2.5, MaxDD ≤ 10%, Sharpe ≥ 2.0 "
             "(from project brief).")
    for title, rows, params, res, mc, note in sections:
        L += ["", "---", "", f"## {title}", "", note, "", hdr, sep, *rows, ""]
        L.append("**Parameters:** `" + type(params).__name__ + "(" + ", ".join(
            f"{k}={v!r}" for k, v in asdict(params).items()) + ")`")
        if mc.get("paths"):
            L.append("")
            L.append(f"**Monte Carlo ({mc['paths']} resamples of OOS trades):** "
                     f"median return {mc['ret_p50']*100:.1f}% "
                     f"(5th {mc['ret_p5']*100:.1f}%, 95th {mc['ret_p95']*100:.1f}%), "
                     f"median MaxDD {mc['dd_p50']*100:.1f}%, "
                     f"P(loss) {mc['p_loss']*100:.0f}%.")
        L += ["", "**OOS equity curve:**", "```", ascii_curve(res.equity), "```"]

    L += ["", "---", "", "## Bottom line", ""]
    L.append("These are the bot's first results on genuine market history. "
             "Where the synthetic-data numbers were stronger than the "
             "real-data numbers, trust the real-data numbers. None of this "
             "authorizes live capital: the required path remains full-history "
             "current data (unrestricted network) → 3–6 months paper trading "
             "→ tiny live pilot.")
    L += ["", "## Appendix — optimization log", "", "```", *log, "```"]
    with open(report_path, "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"\nDone in {time.time()-t0:,.1f}s — report: {report_path}")


if __name__ == "__main__":
    main()
