# TRADING-BOT — Dual-Mode Quantitative Trading System

A research-grade algorithmic trading bot with two modes and asset-class-aware
strategy routing, plus an autonomous backtest/optimization engine with a full
anti-overfitting protocol.

| Component | File |
|---|---|
| Strategy research & design rationale | [`STRATEGY_RESEARCH.md`](STRATEGY_RESEARCH.md) |
| Bot: indicators, strategies, modes, routing, risk | [`trading_bot.py`](trading_bot.py) |
| Engine: data sim, backtester, walk-forward, Monte Carlo, report | [`backtest_engine.py`](backtest_engine.py) |
| Results, equity curves, final parameters, verdicts | [`PERFORMANCE_REPORT.md`](PERFORMANCE_REPORT.md) |

## Architecture

- **Mode 1 — Ultra-Precision Scalper** (minute bars): session VWAP bands,
  volume-delta / CVD confirmation, Bollinger-squeeze release, time-of-day
  filters, time stops, daily loss circuit-breaker.
- **Mode 2 — Macro-Trend Trader** (daily bars): 2-state Markov regime-switching
  filter (filtered probabilities, no lookahead), rolling Hurst exponent, ADX
  gate, TSMOM breakout entries, chandelier trailing stops.
- **Asset routing**: Indices get trend/momentum logic; volatility products
  (VIX/VXX) get z-score mean reversion with a contango/roll-yield gate and a
  vol-of-vol spike overlay. The router refuses mismatched logic.
- **Risk**: fixed-fractional sizing with capped ¼-Kelly overlay, hard stops,
  trailing take-profits.

## Running

```bash
pip install numpy pandas scipy statsmodels yfinance arch
python3 backtest_engine.py    # runs the full autonomous loop, writes PERFORMANCE_REPORT.md
```

yfinance is tried first; when unavailable the engine uses synthetic markets
(GARCH(1,1) + Markov regimes for indices, OU + jumps + contango basis for vol)
per the project spec.

## ⚠️ Read this before risking money

The results in `PERFORMANCE_REPORT.md` come from **synthetic data** and a
demanded-90%-win-rate brief. The report separates real statistical edge from
curve-fit per book (walk-forward OOS, fresh random seeds, Monte Carlo). Even
the passing book has **never seen a live tick**. Do not deploy real capital
without: real historical data revalidation → 3–6 months of paper trading →
tiny-size live pilot. High win rate alone is not an edge.
