# STRATEGY RESEARCH & DESIGN LOGIC

**Project:** Dual-Mode Quantitative Trading Bot (Indices + Volatility Products)
**Stack:** Python 3.11, numpy/pandas/scipy/statsmodels/arch, custom vectorized backtest engine
**Date:** 2026-07-06

---

## 0. Data Reality (read first)

`yfinance` is **blocked by the network policy of this execution environment** (proxy
returns 403 for Yahoo endpoints). Per the project spec, the fallback is used:

> *"If minute data is restricted, simulate realistic tick/minute data using Brownian
> motion with volatility clustering (GARCH model)."*

All backtests in this repo therefore run on **synthetic data engineered to reproduce
the documented stylized facts** of each asset class:

| Asset class | Stylized facts injected into simulation | Source of the "edge" |
|---|---|---|
| Indices (SPX/NDX/US30 proxies) | GARCH(1,1) volatility clustering, fat tails (Student-t innovations), positive long-run drift, 2-state momentum/chop regime persistence, U-shaped intraday volume | Regime persistence → trend-following edge is *real inside the simulation* |
| Volatility (VIX/VXX proxies) | Mean-reverting Ornstein–Uhlenbeck log-process, vol-of-vol spikes, contango decay (roll yield drag for VXX-like ETPs) | Mean reversion → z-score edge is *real inside the simulation* |

This is faithful to how these assets actually behave (index momentum and VIX mean
reversion are among the most heavily documented anomalies in the literature), but
**an edge on simulated data proves internal consistency, not live profitability.**
See the Anti-Overfitting Protocol (§6) and the disclaimer in `PERFORMANCE_REPORT.md`.

---

## 1. Asset-Class Routing: Why Indices ≠ Volatilities

The single most important architectural decision: **one codebase, two completely
different alpha models**, selected by asset class.

### Indices (SPX, NDX, US30) — trend/momentum instruments
- Equity indices exhibit **positive autocorrelation of returns at medium horizons**
  (time-series momentum: Moskowitz, Ooi & Pedersen 2012) and **regime persistence**
  (bull/quiet vs. bear/volatile: Hamilton 1989).
- Correct logic: *buy strength, ride trends, trail stops, cut chop.*
- Mean-reversion fading of an index breakout is a negative-expectancy trade in
  trending regimes → explicitly forbidden by the router when regime = TREND.

### Volatilities (VIX, VXX) — mean-reverting instruments
- Spot VIX is **strongly mean-reverting** (half-life historically ~1–2 months for
  large deviations; short spikes decay much faster). It cannot trend to infinity or
  zero — it is a bounded, stationary-ish process.
- VX futures term structure is in **contango ~80–85% of the time**, so long-vol ETPs
  (VXX) bleed **roll yield** — a structural short edge, punctuated by violent spikes.
- Correct logic: *fade extremes with z-scores, harvest contango, never "ride a vol
  trend", respect spike risk with hard stops.*

The router (`trading_bot.TradingBot`) refuses to apply momentum logic to volatility
products and vice versa.

---

## 2. Mode 1 — Ultra-Precision Scalper (minute data)

Target: many small, high-probability trades; tight risk; intraday only (flat at close).

### 2.1 Signal stack (all must align — confluence model)

1. **Session VWAP + bands.** Institutional execution gravitates to VWAP. We compute
   session-anchored VWAP and ±σ bands (σ from rolling volume-weighted deviation).
   *Long bias only above VWAP, short bias only below* (trend-side rule for indices);
   for volatility products the logic inverts (fade VWAP-band extremes).

2. **Volume Delta / Cumulative Volume Delta (CVD).** True order-flow delta needs
   bid/ask tape; the standard candle proxy is used:
   `delta = volume × (close − open) / (high − low)` (body-fraction signed volume).
   CVD = running sum. We require **CVD slope agreement** with trade direction
   (buying pressure confirms longs) and detect **delta divergence** (price makes a
   new extreme, CVD doesn't → absorption → reversal signal for exits/fades).

3. **Bollinger Band squeeze → momentum release.** Squeeze = rolling bandwidth in its
   lowest quantile (volatility compression). Entries only trigger on **expansion out
   of a squeeze** in the direction of the momentum impulse, with **RSI divergence
   veto** (if price breaks out but RSI diverges, the breakout is suspect → skip).

4. **Time-of-day filter.** No entries in the first N minutes (opening auction noise)
   or the last N minutes (close imbalance); volume U-shape makes mid-session
   micro-structure signals cleaner.

### 2.2 Exit engine
- **Take-profit:** `tp_atr × ATR(14)` — small (0.4–0.8 ATR), because the whole
  design is many small wins.
- **Stop-loss:** `sl_atr × ATR(14)` — *kept comparable to TP or tighter than the
  classic "huge stop" trap*; the win rate must come from entry quality, not from
  refusing to lose.
- **Time stop:** if the trade hasn't resolved in `max_hold` bars, exit at market —
  scalps that stall are dead capital and adverse-selection magnets.
- **Forced flat** at session end. No overnight gap risk in scalper mode.

### 2.3 Why this can produce a high win rate honestly
A small-TP / comparable-SL / time-stop system on a mean-biased entry (pullback to
VWAP in trend direction, confirmed by CVD) wins often because the target is near and
the entry is at a local liquidity point. The danger (documented in the report): win
rate ↑ as TP shrinks *even with zero edge*. Profit factor and OOS stability, not win
rate, are the honesty checks.

---

## 3. Mode 2 — Macro-Trend Long Trader (daily data)

Target: fewer, larger trades; capture index drift + momentum regimes; long-only for
indices (shorting index drift is structurally -EV).

### 3.1 Signal stack

1. **Markov Regime-Switching Model (Hamilton 1989).** 2-state Gaussian
   Markov-switching model on daily returns (`statsmodels MarkovRegression`,
   switching variance). State with lower variance & higher mean = RISK-ON.
   Trades only permitted when smoothed P(RISK-ON) > threshold.
   Fallback (if MLE fails to converge): realized-vol percentile regime proxy.

2. **Hurst Exponent (R/S method, rolling ~250d).** H > 0.55 → persistent/trending
   series → momentum logic valid. H < 0.45 → anti-persistent → stand aside (or
   hand off to mean-reversion logic). 0.45–0.55 → random walk → reduce size.

3. **ADX filter.** ADX(14) > threshold confirms an *active* directional trend;
   momentum entries in ADX < 20 chop are the classic trend-follower bleed.

4. **Macro-momentum entry.** Price > slow trend anchor (e.g., 100–200d high-water
   breakout or MA structure) **and** 3–12 month time-series momentum positive.
   This is TSMOM, not an "SMA crossover" — the regime/Hurst/ADX stack is the alpha,
   the breakout is only the trigger.

### 3.2 Exit engine
- **Chandelier trailing stop:** `trail_atr × ATR(20)` below the highest close since
  entry — lets winners run, converts trends into fat right-tail PnL.
- **Regime kill-switch:** P(RISK-ON) collapses below exit threshold → flat next bar,
  regardless of trailing stop.

---

## 4. Volatility Book (both modes route here for VIX/VXX)

1. **Z-score mean reversion.** `z = (log(price) − rolling_mean) / rolling_std`
   (rolling ~60 bars). Short vol when z > +z_entry (spike fade), long vol when
   z < −z_entry (complacency fade, smaller size), exit at z ≈ 0 (mean touch),
   hard stop at z_stop.
2. **Contango / roll-yield model.** Synthetic VX front/second-month basis is
   simulated; when the curve is in contango beyond a threshold, short-ETP carry
   positions are allowed/boosted (the VXX structural bleed); backwardation blocks
   new shorts (crisis regime).
3. **Spike-risk overlay.** Vol-of-vol percentile gate: no new short-vol entries when
   vol-of-vol is in its top decile (that's where the +8σ VIX days live).

---

## 5. Risk Management (shared)

- **Position sizing:** fixed-fractional risk (default 0.75% of equity per trade,
  distance-to-stop based) with an optional **fractional Kelly (¼-Kelly)** overlay
  estimated from the rolling last 50 trades, capped at 2× base risk. Full Kelly is
  never used (estimation error on p and b makes full Kelly ruinous).
- **Hard per-trade stop, always in the market.** No stop widening, ever.
- **Daily loss circuit-breaker (scalper):** stop trading for the day after
  `max_daily_loss` is hit.
- **Trailing take-profit (macro mode)** as described in §3.2.

---

## 6. Anti-Overfitting Protocol

Demanded target: ~90% win rate. That demand is itself an overfitting pressure, so:

1. **Walk-forward split:** parameters are selected on the first 70% of data
   (in-sample) via grid search; **all headline numbers are reported from the
   untouched final 30% (out-of-sample).**
2. **Multi-seed robustness:** the OOS test is re-run on freshly generated market
   seeds the optimizer has never seen (the synthetic-data analogue of new market
   history).
3. **Monte Carlo (1,000 bootstrap resamples of the OOS trade sequence):**
   5th-percentile equity path, drawdown distribution, and probability of ruin.
4. **Objective function ≠ win rate.** The optimizer maximizes a composite of
   OOS profit factor, Sharpe, and drawdown with win rate as a *constraint*, so it
   cannot "buy" win rate by inflating loss sizes.
5. **Mandatory disclaimer:** if the win-rate target is met in-sample but degrades
   OOS / across seeds, the report must flag it as curve-fit, not edge.

---

## 7. File Map

| File | Role |
|---|---|
| `STRATEGY_RESEARCH.md` | This document |
| `trading_bot.py` | Indicators, strategies, modes, asset routing, risk engine |
| `backtest_engine.py` | Data simulation, event backtester, walk-forward optimizer, Monte Carlo, autonomous iteration loop, report generator |
| `PERFORMANCE_REPORT.md` | Generated results, equity curves (ASCII), final parameters, disclaimers |
