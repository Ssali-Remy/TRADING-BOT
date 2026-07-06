# PERFORMANCE REPORT — Dual-Mode Quant Trading Bot

*Generated 2026-07-06 19:09 — engine runtime 29s — data source: yfinance blocked by network policy -> synthetic GARCH/OU markets per project spec.*

## ⚠️ MANDATORY DISCLAIMER — READ BEFORE ANY CAPITAL DECISION

1. **All results below are from SYNTHETIC market data** (GARCH/OU simulations built to reproduce documented stylized facts). Yahoo Finance is blocked by this environment's network policy. An edge on simulated data proves internal consistency of the logic — **it is NOT evidence of live-market profitability.**
2. **Win rate is the least trustworthy metric here.** A high win rate is trivially manufactured by taking small targets; the honesty checks are profit factor, payoff ratio, OOS stability and fresh-seed stability, all reported below.
3. **Where a target is met in-sample but degrades out-of-sample or on fresh seeds, treat it as curve-fit, not edge.** Each book's verdict below states this explicitly.
4. **This system is NOT ready for real money.** It has never seen a live tick. Minimum path: real historical data → paper trading 3–6 months → tiny live size. See §Deployment.

## Targets (from project brief)

| Metric | Target |
|---|---|
| Win rate | ≥ 85% |
| Profit factor | ≥ 2.5 |
| Max drawdown | ≤ 10% |
| Sharpe | ≥ 2.0 |
| Min trades for validity | 25 |


---

## SPX-SCALPER (Mode 1, Index, minute)

| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |
|---|---|---|---|---|---|---|---|
| In-sample (70%, optimized) | 591 | 69.4% | 1.20 | 2.02 | 8.65% | 13.49% | 0.53 |
| **Out-of-sample (30%, untouched)** | 272 | 75.4% | 0.97 | -0.73 | 9.20% | -1.13% | 0.32 |
| Fresh seed 1 (never seen) | 875 | 72.5% | 0.98 | -0.01 | 7.54% | -1.88% | 0.37 |
| Fresh seed 2 (never seen) | 876 | 72.7% | 1.15 | 1.50 | 9.04% | 15.18% | 0.43 |
| Fresh seed 3 (never seen) | 899 | 71.9% | 1.18 | 1.49 | 11.73% | 12.53% | 0.46 |

**Verdict:** **PARTIAL** — OOS misses target(s): win_rate, profit_factor, sharpe. Honest edge may exist but does not reach the demanded thresholds without overfitting; the optimizer deliberately refused to buy win rate with larger losses.

**Final parameters:**
```python
ScalperParams(vwap_band_k=1.5, fade_k=1.8, fade_tp_frac=0.5, cvd_slope_window=12, bb_window=20, bb_k=2.0, squeeze_quantile=0.25, squeeze_lookback=240, rsi_window=14, atr_window=14, tp_atr=2.0, sl_atr=7.0, max_hold=90, open_skip=15, close_skip=15, trend_ma=60)
```

**Monte Carlo (1000 bootstrap resamples of the OOS trade sequence):** median return -1.0% (5th pct -12.6%, 95th pct 11.1%); median MaxDD 7.9% (95th pct 15.9%); P(net loss) 55.1%; P(drawdown >20%) 0.9%.

**Out-of-sample equity curve (ASCII):**
```
     107,560 |                                      █                         
             |                                      ·                         
             |                                      · █                       
             |                                     █·█· █                     
             |                                     ····█·                     
             |                           █         ······                     
             |                           ·        █······█                    
             |  █                   █   █·       █········█                   
             |  ·                   ·███·· █     ··········█        █         
             | █·█               █  ······█·██ ██···········    ████·█  █     
             |█···███   █     ███·██··········█·············████······██·     
      98,869 |·······███·█████···········································█████
             ----------------------------------------------------------------
```

---

## SPX-MACRO (Mode 2, Index, daily)

| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |
|---|---|---|---|---|---|---|---|
| In-sample (70%, optimized) | 27 | 55.6% | 2.01 | 0.42 | 8.97% | 18.29% | 1.61 |
| **Out-of-sample (30%, untouched)** | 8 | 75.0% | 2.74 | 0.53 | 3.47% | 5.45% | 0.91 |
| Fresh seed 1 (never seen) | 32 | 53.1% | 3.47 | 0.77 | 9.41% | 63.33% | 3.06 |
| Fresh seed 2 (never seen) | 38 | 47.4% | 1.61 | 0.37 | 19.32% | 28.14% | 1.78 |
| Fresh seed 3 (never seen) | 30 | 56.7% | 3.89 | 0.60 | 9.95% | 44.11% | 2.97 |

**Verdict:** **PARTIAL** — OOS misses target(s): win_rate, sharpe, trade count (8 < 15). Honest edge may exist but does not reach the demanded thresholds without overfitting; the optimizer deliberately refused to buy win rate with larger losses.

**Final parameters:**
```python
MacroParams(regime_prob_entry=0.65, regime_prob_exit=0.4, hurst_window=250, hurst_min=0.53, adx_window=14, adx_min=12.0, mom_lookback=126, breakout_lookback=20, atr_window=20, trail_atr=2.5, sl_atr=3.0)
```

**Monte Carlo (1000 bootstrap resamples of the OOS trade sequence):** median return 5.3% (5th pct -1.8%, 95th pct 12.9%); median MaxDD 1.7% (95th pct 4.5%); P(net loss) 11.8%; P(drawdown >20%) 0.0%.

**Out-of-sample equity curve (ASCII):**
```
     107,512 |                                                █               
             |                                             █ █·               
             |                                             ·█··     █         
             |                                             ····     ·         
             |                                             ····     ·█████████
             |                                           ██····█████··········
             |                                           ·····················
             |                                           ·····················
             |                                           ·····················
             |                                          █·····················
             |               ███████████████████████████······················
     100,000 |███████████████·················································
             ----------------------------------------------------------------
```

---

## VXX-SCALP-MR (Mode 1, Volatility, minute)

| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |
|---|---|---|---|---|---|---|---|
| In-sample (70%, optimized) | 108 | 88.0% | 4.23 | 9.04 | 2.64% | 28.41% | 0.58 |
| **Out-of-sample (30%, untouched)** | 45 | 91.1% | 7.03 | 8.96 | 1.62% | 12.16% | 0.69 |
| Fresh seed 1 (never seen) | 162 | 84.0% | 11.05 | 10.85 | 1.78% | 55.06% | 2.11 |
| Fresh seed 2 (never seen) | 167 | 87.4% | 4.24 | 9.50 | 2.34% | 52.89% | 0.61 |
| Fresh seed 3 (never seen) | 155 | 84.5% | 3.96 | 8.82 | 2.98% | 42.76% | 0.73 |

**Verdict:** **PASS (out-of-sample)** — all targets met on the untouched final 30%. Fresh-seed runs meet every target strictly on 1/3 seeds (misses are marginal — see table); every seed is strongly profitable, so the edge is real within the simulation, but the exact 85% win-rate line is not guaranteed on every market realization.

**Final parameters:**
```python
VolParams(z_window=585, z_entry_short=1.8, z_entry_long=-2.0, z_exit=0.6000000000000001, z_stop=3.2, atr_window=14, sl_atr=1.5, max_hold=60, contango_gate=0.0, vov_window=60, vov_max_pct=0.9, long_size_mult=0.5)
```

**Monte Carlo (1000 bootstrap resamples of the OOS trade sequence):** median return 12.1% (5th pct 7.4%, 95th pct 17.0%); median MaxDD 1.5% (95th pct 2.5%); P(net loss) 0.0%; P(drawdown >20%) 0.0%.

**Out-of-sample equity curve (ASCII):**
```
     112,325 |                                                             ██ 
             |                                                        █████··█
             |                                                       █········
             |                                                     ██·········
             |                                         ████████████···········
             |                                      ███·······················
             |                                █   ██··························
             |                                ·███····························
             |                            ████································
             |                      ██████····································
             |            ██████████··········································
     100,000 |████████████····················································
             ----------------------------------------------------------------
```

---

## VIX-MACRO-MR (Mode 2, Volatility, daily)

| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |
|---|---|---|---|---|---|---|---|
| In-sample (70%, optimized) | 36 | 69.4% | 2.70 | 0.55 | 2.57% | 24.50% | 1.19 |
| **Out-of-sample (30%, untouched)** | 16 | 68.8% | 1.45 | 0.25 | 4.01% | 2.80% | 0.66 |
| Fresh seed 1 (never seen) | 43 | 81.4% | 4.26 | 0.43 | 9.08% | 43.27% | 0.97 |
| Fresh seed 2 (never seen) | 60 | 71.7% | 1.60 | 0.24 | 14.19% | 22.27% | 0.63 |
| Fresh seed 3 (never seen) | 51 | 70.6% | 1.96 | 0.22 | 20.92% | 35.98% | 0.82 |

**Verdict:** **PARTIAL** — OOS misses target(s): win_rate, profit_factor, sharpe. Honest edge may exist but does not reach the demanded thresholds without overfitting; the optimizer deliberately refused to buy win rate with larger losses.

**Final parameters:**
```python
VolParams(z_window=40, z_entry_short=2.2, z_entry_long=-2.0, z_exit=0.4, z_stop=3.2, atr_window=14, sl_atr=1.5, max_hold=40, contango_gate=0.0, vov_window=60, vov_max_pct=0.9, long_size_mult=0.5)
```

**Monte Carlo (1000 bootstrap resamples of the OOS trade sequence):** median return 2.8% (5th pct -3.9%, 95th pct 9.3%); median MaxDD 3.0% (95th pct 6.2%); P(net loss) 25.1%; P(drawdown >20%) 0.0%.

**Out-of-sample equity curve (ASCII):**
```
     103,855 |                     █████████                                  
             |                     ·········                                  
             |                     ·········                                  
             |                    █·········                                  
             |               ███  ··········        █                █████████
             |               ···  ··········██      ·                ·········
             |               ···██············     █·                ·········
             |              █·················████ ··                ·········
             |       ███████······················█··███       ██████·········
             |   ████···································       ···············
             |   ·······································       ···············
     100,000 |███·······································███████···············
             ----------------------------------------------------------------
```

---

## Deployment status

**NOT deployed to live capital, and it must not be.** This engine has no broker connection, and this environment blocks market-data endpoints. Required path before any real money:

1. Re-run the full walk-forward + Monte Carlo protocol on **real** historical data (yfinance/Polygon/IBKR) from an unrestricted network.
2. Paper-trade via a broker sandbox (e.g. IBKR paper account) for **3–6 months minimum**, comparing live fills vs. backtest assumptions (slippage, spread, latency).
3. Only if paper results match backtest distributions within Monte Carlo bands, deploy **tiny** size with the daily circuit-breaker armed.

## Appendix — full optimization iteration log

```

### SPX-SCALPER (Mode 1, Index, minute) — optimization log
  iter   1 [grid] trades= 916  WR= 64.4%  PF= 0.93  Sharpe= -0.84  MaxDD=15.06%  Ret=  -8.01%
  iter   2 [grid] trades= 896  WR= 65.0%  PF= 0.86  Sharpe= -2.04  MaxDD=17.97%  Ret= -14.42%
  iter   3 [grid] trades= 814  WR= 61.7%  PF= 0.85  Sharpe= -1.67  MaxDD=19.86%  Ret= -13.79%
  iter   4 [grid] trades= 796  WR= 61.3%  PF= 0.78  Sharpe= -3.28  MaxDD=18.77%  Ret= -17.35%
  iter   5 [grid] trades= 810  WR= 68.5%  PF= 0.90  Sharpe= -1.46  MaxDD=12.80%  Ret=  -8.83%
  iter   6 [grid] trades= 792  WR= 69.6%  PF= 0.96  Sharpe= -0.45  MaxDD=12.89%  Ret=  -3.68%
  iter   7 [grid] trades= 744  WR= 66.0%  PF= 0.87  Sharpe= -1.38  MaxDD=17.65%  Ret= -10.32%
  iter   8 [grid] trades= 713  WR= 66.3%  PF= 1.02  Sharpe=  0.47  MaxDD=11.94%  Ret=   2.48%
  iter   9 [grid] trades= 720  WR= 72.2%  PF= 1.09  Sharpe=  1.10  MaxDD=10.02%  Ret=   6.79%
  iter  10 [grid] trades= 688  WR= 75.0%  PF= 1.01  Sharpe=  0.19  MaxDD=10.86%  Ret=   0.45%
  iter  11 [grid] trades= 664  WR= 69.3%  PF= 0.95  Sharpe= -0.24  MaxDD= 9.98%  Ret=  -3.35%
  iter  12 [grid] trades= 616  WR= 72.4%  PF= 1.10  Sharpe=  1.19  MaxDD= 9.90%  Ret=   8.14%
  iter  13 [grid] trades= 731  WR= 62.4%  PF= 0.95  Sharpe= -0.28  MaxDD=13.31%  Ret=  -5.30%
  iter  14 [grid] trades= 718  WR= 63.0%  PF= 0.99  Sharpe=  0.27  MaxDD=13.12%  Ret=  -0.92%
  iter  15 [grid] trades= 666  WR= 59.9%  PF= 0.96  Sharpe= -0.09  MaxDD=13.34%  Ret=  -3.69%
  iter  16 [grid] trades= 653  WR= 59.0%  PF= 0.84  Sharpe= -1.79  MaxDD=17.40%  Ret= -12.46%
  iter  17 [grid] trades= 652  WR= 66.0%  PF= 1.14  Sharpe=  1.74  MaxDD=12.86%  Ret=  15.34%
  iter  18 [grid] trades= 632  WR= 67.7%  PF= 1.01  Sharpe=  0.28  MaxDD=13.09%  Ret=   0.97%
  iter  19 [grid] trades= 606  WR= 63.9%  PF= 1.20  Sharpe=  2.27  MaxDD=12.69%  Ret=  22.66%
  iter  20 [grid] trades= 574  WR= 64.5%  PF= 1.11  Sharpe=  1.30  MaxDD=11.59%  Ret=   9.04%
  iter  21 [grid] trades= 591  WR= 69.4%  PF= 1.20  Sharpe=  2.02  MaxDD= 8.65%  Ret=  13.49%
  iter  22 [grid] trades= 558  WR= 72.4%  PF= 0.93  Sharpe= -0.47  MaxDD=11.17%  Ret=  -3.89%
  iter  23 [grid] trades= 548  WR= 67.0%  PF= 1.17  Sharpe=  1.78  MaxDD= 8.34%  Ret=  11.85%
  iter  24 [grid] trades= 505  WR= 68.9%  PF= 1.07  Sharpe=  0.77  MaxDD=11.24%  Ret=   4.56%
  iter  25 [grid] trades= 575  WR= 60.5%  PF= 0.96  Sharpe= -0.19  MaxDD= 9.74%  Ret=  -3.51%
  iter  26 [grid] trades= 570  WR= 61.1%  PF= 0.98  Sharpe=  0.09  MaxDD= 9.20%  Ret=  -1.44%
  iter  27 [grid] trades= 543  WR= 58.6%  PF= 1.02  Sharpe=  0.48  MaxDD=10.37%  Ret=   1.51%
  iter  28 [grid] trades= 524  WR= 57.8%  PF= 0.91  Sharpe= -0.76  MaxDD=13.56%  Ret=  -7.01%
  iter  29 [grid] trades= 522  WR= 64.0%  PF= 0.80  Sharpe= -2.00  MaxDD=11.70%  Ret=  -9.34%
  iter  30 [grid] trades= 497  WR= 65.0%  PF= 0.99  Sharpe=  0.09  MaxDD=10.64%  Ret=  -0.88%
  iter  31 [grid] trades= 500  WR= 61.8%  PF= 0.92  Sharpe= -0.75  MaxDD=11.38%  Ret=  -5.79%
  iter  32 [grid] trades= 471  WR= 61.6%  PF= 0.96  Sharpe= -0.28  MaxDD=10.87%  Ret=  -3.19%
  iter  33 [grid] trades= 468  WR= 67.9%  PF= 1.07  Sharpe=  0.84  MaxDD= 7.50%  Ret=   3.80%
  iter  34 [grid] trades= 436  WR= 69.7%  PF= 0.93  Sharpe= -0.53  MaxDD= 9.21%  Ret=  -3.30%
  iter  35 [grid] trades= 452  WR= 65.5%  PF= 0.85  Sharpe= -1.54  MaxDD= 8.06%  Ret=  -6.16%
  iter  36 [grid] trades= 420  WR= 67.6%  PF= 1.06  Sharpe=  0.59  MaxDD= 9.25%  Ret=   3.40%
  iter  37 [refine tp_atr=1.5] trades= 634  WR= 72.1%  PF= 0.92  Sharpe= -0.67  MaxDD= 7.35%  Ret=  -4.12%
  iter  38 [refine tp_atr=2.5] trades= 570  WR= 67.9%  PF= 1.02  Sharpe=  0.32  MaxDD=10.00%  Ret=   1.04%
  iter  39 [refine cvd_slope_window=8] trades= 603  WR= 69.7%  PF= 1.07  Sharpe=  0.88  MaxDD= 9.32%  Ret=   4.16%
  iter  40 [refine cvd_slope_window=18] trades= 588  WR= 69.6%  PF= 1.14  Sharpe=  1.41  MaxDD= 6.80%  Ret=   8.28%
  BEST (in-sample): trades= 591  WR= 69.4%  PF= 1.20  Sharpe=  2.02  MaxDD= 8.65%  Ret=  13.49%

### SPX-MACRO (Mode 2, Index, daily) — optimization log
  iter   1 [grid] trades=  31  WR= 51.6%  PF= 1.12  Sharpe=  0.08  MaxDD= 9.57%  Ret=   2.12%
  iter   2 [grid] trades=  29  WR= 48.3%  PF= 0.93  Sharpe= -0.03  MaxDD= 8.09%  Ret=  -0.84%
  iter   3 [grid] trades=  20  WR= 45.0%  PF= 1.59  Sharpe=  0.27  MaxDD= 5.56%  Ret=   8.78%
  iter   4 [grid] trades=  28  WR= 42.9%  PF= 1.64  Sharpe=  0.32  MaxDD=12.59%  Ret=  15.92%
  iter   5 [grid] trades=  27  WR= 44.4%  PF= 0.79  Sharpe= -0.11  MaxDD= 9.21%  Ret=  -2.88%
  iter   6 [grid] trades=  18  WR= 50.0%  PF= 1.53  Sharpe=  0.23  MaxDD= 6.22%  Ret=   7.58%
  iter   7 [grid] trades=  28  WR= 39.3%  PF= 1.26  Sharpe=  0.16  MaxDD=12.29%  Ret=   6.68%
  iter   8 [grid] trades=  27  WR= 37.0%  PF= 0.63  Sharpe= -0.24  MaxDD=11.14%  Ret=  -5.89%
  iter   9 [grid] trades=  18  WR= 38.9%  PF= 1.10  Sharpe=  0.06  MaxDD= 8.04%  Ret=   1.57%
  iter  10 [grid] trades=  27  WR= 55.6%  PF= 2.05  Sharpe=  0.44  MaxDD=10.32%  Ret=  22.74%
  iter  11 [grid] trades=  26  WR= 50.0%  PF= 1.33  Sharpe=  0.19  MaxDD= 8.90%  Ret=   6.94%
  iter  12 [grid] trades=  18  WR= 44.4%  PF= 1.53  Sharpe=  0.24  MaxDD= 5.93%  Ret=   7.35%
  iter  13 [grid] trades=  25  WR= 48.0%  PF= 1.52  Sharpe=  0.25  MaxDD=11.50%  Ret=  11.02%
  iter  14 [grid] trades=  25  WR= 44.0%  PF= 1.12  Sharpe=  0.08  MaxDD=11.20%  Ret=   2.13%
  iter  15 [grid] trades=  17  WR= 47.1%  PF= 1.27  Sharpe=  0.14  MaxDD= 8.38%  Ret=   3.95%
  iter  16 [grid] trades=  25  WR= 44.0%  PF= 1.18  Sharpe=  0.11  MaxDD=10.66%  Ret=   3.85%
  iter  17 [grid] trades=  25  WR= 36.0%  PF= 0.95  Sharpe= -0.02  MaxDD=13.09%  Ret=  -0.83%
  iter  18 [grid] trades=  17  WR= 35.3%  PF= 0.91  Sharpe= -0.03  MaxDD= 9.91%  Ret=  -1.42%
  iter  19 [grid] trades=  30  WR= 50.0%  PF= 0.99  Sharpe=  0.00  MaxDD= 7.51%  Ret=  -0.15%
  iter  20 [grid] trades=  27  WR= 48.1%  PF= 0.90  Sharpe= -0.05  MaxDD= 8.79%  Ret=  -1.26%
  iter  21 [grid] trades=  19  WR= 42.1%  PF= 1.40  Sharpe=  0.20  MaxDD= 6.15%  Ret=   6.09%
  iter  22 [grid] trades=  28  WR= 39.3%  PF= 0.83  Sharpe= -0.09  MaxDD= 9.04%  Ret=  -2.32%
  iter  23 [grid] trades=  25  WR= 44.0%  PF= 0.76  Sharpe= -0.14  MaxDD= 9.78%  Ret=  -3.36%
  iter  24 [grid] trades=  17  WR= 47.1%  PF= 1.33  Sharpe=  0.17  MaxDD= 7.00%  Ret=   4.87%
  iter  25 [grid] trades=  28  WR= 35.7%  PF= 0.67  Sharpe= -0.22  MaxDD=10.97%  Ret=  -5.07%
  iter  26 [grid] trades=  25  WR= 36.0%  PF= 0.60  Sharpe= -0.26  MaxDD=11.69%  Ret=  -6.34%
  iter  27 [grid] trades=  17  WR= 35.3%  PF= 1.05  Sharpe=  0.04  MaxDD= 8.17%  Ret=   0.79%
  iter  28 [grid] trades=  26  WR= 53.8%  PF= 0.90  Sharpe= -0.04  MaxDD= 8.43%  Ret=  -1.22%
  iter  29 [grid] trades=  24  WR= 50.0%  PF= 1.47  Sharpe=  0.24  MaxDD= 9.47%  Ret=   8.79%
  iter  30 [grid] trades=  17  WR= 41.2%  PF= 1.34  Sharpe=  0.17  MaxDD= 6.52%  Ret=   4.87%
  iter  31 [grid] trades=  25  WR= 44.0%  PF= 0.68  Sharpe= -0.20  MaxDD=11.26%  Ret=  -4.66%
  iter  32 [grid] trades=  23  WR= 43.5%  PF= 1.11  Sharpe=  0.08  MaxDD=11.77%  Ret=   1.87%
  iter  33 [grid] trades=  16  WR= 43.8%  PF= 1.15  Sharpe=  0.09  MaxDD= 8.96%  Ret=   2.32%
  iter  34 [grid] trades=  25  WR= 40.0%  PF= 0.55  Sharpe= -0.31  MaxDD=13.14%  Ret=  -7.34%
  iter  35 [grid] trades=  23  WR= 34.8%  PF= 0.92  Sharpe= -0.03  MaxDD=13.64%  Ret=  -1.30%
  iter  36 [grid] trades=  16  WR= 31.2%  PF= 0.87  Sharpe= -0.06  MaxDD=10.47%  Ret=  -2.29%
  iter  37 [grid] trades=  27  WR= 44.4%  PF= 1.34  Sharpe=  0.20  MaxDD= 8.66%  Ret=   7.57%
  iter  38 [grid] trades=  24  WR= 41.7%  PF= 1.19  Sharpe=  0.12  MaxDD= 9.46%  Ret=   3.43%
  iter  39 [grid] trades=  17  WR= 41.2%  PF= 1.67  Sharpe=  0.27  MaxDD= 5.20%  Ret=   8.10%
  iter  40 [grid] trades=  25  WR= 36.0%  PF= 1.15  Sharpe=  0.11  MaxDD=10.23%  Ret=   3.53%
  iter  41 [grid] trades=  22  WR= 40.9%  PF= 1.11  Sharpe=  0.08  MaxDD= 9.84%  Ret=   2.11%
  iter  42 [grid] trades=  15  WR= 46.7%  PF= 1.50  Sharpe=  0.22  MaxDD= 6.95%  Ret=   6.41%
  iter  43 [grid] trades=  25  WR= 32.0%  PF= 1.07  Sharpe=  0.06  MaxDD=11.80%  Ret=   1.40%
  iter  44 [grid] trades=  22  WR= 31.8%  PF= 1.05  Sharpe=  0.04  MaxDD=11.43%  Ret=   0.92%
  iter  45 [grid] trades=  15  WR= 33.3%  PF= 1.09  Sharpe=  0.06  MaxDD= 8.92%  Ret=   1.34%
  iter  46 [grid] trades=  23  WR= 47.8%  PF= 1.51  Sharpe=  0.26  MaxDD= 8.77%  Ret=  10.33%
  iter  47 [grid] trades=  21  WR= 42.9%  PF= 1.25  Sharpe=  0.15  MaxDD= 9.58%  Ret=   4.50%
  iter  48 [grid] trades=  15  WR= 40.0%  PF= 1.73  Sharpe=  0.28  MaxDD= 5.19%  Ret=   7.98%
  iter  49 [grid] trades=  22  WR= 40.9%  PF= 1.14  Sharpe=  0.10  MaxDD=11.32%  Ret=   3.07%
  iter  50 [grid] trades=  20  WR= 40.0%  PF= 1.12  Sharpe=  0.08  MaxDD=11.79%  Ret=   1.99%
  iter  51 [grid] trades=  14  WR= 42.9%  PF= 1.26  Sharpe=  0.13  MaxDD= 7.61%  Ret=   3.54%
  iter  52 [grid] trades=  22  WR= 36.4%  PF= 1.06  Sharpe=  0.05  MaxDD=12.87%  Ret=   1.03%
  iter  53 [grid] trades=  20  WR= 30.0%  PF= 0.92  Sharpe= -0.03  MaxDD=13.34%  Ret=  -1.47%
  iter  54 [grid] trades=  14  WR= 28.6%  PF= 0.91  Sharpe= -0.03  MaxDD= 9.23%  Ret=  -1.39%
  iter  55 [refine trail_atr=2.0] trades=  29  WR= 51.7%  PF= 1.19  Sharpe=  0.13  MaxDD= 7.49%  Ret=   3.69%
  iter  56 [refine trail_atr=3.125] trades=  25  WR= 56.0%  PF= 1.78  Sharpe=  0.34  MaxDD=11.08%  Ret=  15.60%
  iter  57 [refine sl_atr=2.0] trades=  28  WR= 53.6%  PF= 2.03  Sharpe=  0.49  MaxDD=10.17%  Ret=  30.59%
  iter  58 [refine sl_atr=3.0] trades=  27  WR= 55.6%  PF= 2.01  Sharpe=  0.42  MaxDD= 8.97%  Ret=  18.29%
  BEST (in-sample): trades=  27  WR= 55.6%  PF= 2.01  Sharpe=  0.42  MaxDD= 8.97%  Ret=  18.29%

### VXX-SCALP-MR (Mode 1, Volatility, minute) — optimization log
  iter   1 [grid] trades= 198  WR= 78.3%  PF= 2.64  Sharpe=  7.92  MaxDD= 3.07%  Ret=  35.57%
  iter   2 [grid] trades= 190  WR= 77.9%  PF= 2.77  Sharpe=  7.22  MaxDD= 2.67%  Ret=  24.37%
  iter   3 [grid] trades= 209  WR= 78.5%  PF= 2.87  Sharpe=  8.46  MaxDD= 2.56%  Ret=  35.48%
  iter   4 [grid] trades= 203  WR= 78.3%  PF= 2.91  Sharpe=  7.69  MaxDD= 2.28%  Ret=  24.18%
  iter   5 [grid] trades= 139  WR= 81.3%  PF= 2.83  Sharpe=  7.07  MaxDD= 2.75%  Ret=  30.29%
  iter   6 [grid] trades= 135  WR= 80.7%  PF= 2.94  Sharpe=  6.93  MaxDD= 2.07%  Ret=  21.70%
  iter   7 [grid] trades= 143  WR= 81.1%  PF= 2.86  Sharpe=  6.83  MaxDD= 2.49%  Ret=  26.25%
  iter   8 [grid] trades= 140  WR= 81.4%  PF= 3.13  Sharpe=  7.09  MaxDD= 2.07%  Ret=  21.11%
  iter   9 [grid] trades= 105  WR= 81.9%  PF= 4.20  Sharpe=  9.43  MaxDD= 2.64%  Ret=  35.47%
  iter  10 [grid] trades= 105  WR= 81.9%  PF= 3.77  Sharpe=  9.26  MaxDD= 2.17%  Ret=  25.23%
  iter  11 [grid] trades= 107  WR= 86.0%  PF= 4.36  Sharpe=  9.36  MaxDD= 2.64%  Ret=  32.59%  << TARGETS MET
  iter  12 [grid] trades= 107  WR= 86.0%  PF= 3.83  Sharpe=  8.93  MaxDD= 2.17%  Ret=  22.93%  << TARGETS MET
  iter  13 [grid] trades= 169  WR= 77.5%  PF= 2.87  Sharpe=  7.85  MaxDD= 2.42%  Ret=  31.90%
  iter  14 [grid] trades= 163  WR= 77.3%  PF= 3.36  Sharpe=  8.36  MaxDD= 2.04%  Ret=  24.06%
  iter  15 [grid] trades= 175  WR= 79.4%  PF= 3.15  Sharpe=  8.43  MaxDD= 2.42%  Ret=  31.00%
  iter  16 [grid] trades= 171  WR= 79.5%  PF= 3.58  Sharpe=  9.06  MaxDD= 1.96%  Ret=  23.36%
  iter  17 [grid] trades= 110  WR= 79.1%  PF= 2.51  Sharpe=  5.31  MaxDD= 2.56%  Ret=  19.59%
  iter  18 [grid] trades= 106  WR= 79.2%  PF= 2.93  Sharpe=  5.83  MaxDD= 2.05%  Ret=  15.12%
  iter  19 [grid] trades= 113  WR= 80.5%  PF= 2.75  Sharpe=  5.90  MaxDD= 2.56%  Ret=  20.86%
  iter  20 [grid] trades= 109  WR= 80.7%  PF= 3.33  Sharpe=  6.51  MaxDD= 2.05%  Ret=  16.17%
  iter  21 [grid] trades=  83  WR= 78.3%  PF= 3.60  Sharpe=  7.00  MaxDD= 2.12%  Ret=  22.72%
  iter  22 [grid] trades=  83  WR= 79.5%  PF= 4.10  Sharpe=  7.69  MaxDD= 1.80%  Ret=  17.99%
  iter  23 [grid] trades=  85  WR= 83.5%  PF= 3.46  Sharpe=  6.56  MaxDD= 2.29%  Ret=  20.80%
  iter  24 [grid] trades=  85  WR= 84.7%  PF= 3.86  Sharpe=  7.21  MaxDD= 1.80%  Ret=  16.37%
  iter  25 [grid] trades= 143  WR= 78.3%  PF= 3.06  Sharpe=  6.83  MaxDD= 2.39%  Ret=  27.72%
  iter  26 [grid] trades= 138  WR= 77.5%  PF= 3.69  Sharpe=  7.15  MaxDD= 2.17%  Ret=  21.00%
  iter  27 [grid] trades= 148  WR= 79.1%  PF= 3.17  Sharpe=  7.08  MaxDD= 2.39%  Ret=  25.82%
  iter  28 [grid] trades= 145  WR= 78.6%  PF= 3.59  Sharpe=  7.34  MaxDD= 2.17%  Ret=  19.42%
  iter  29 [grid] trades=  92  WR= 79.3%  PF= 2.93  Sharpe=  5.32  MaxDD= 3.07%  Ret=  17.50%
  iter  30 [grid] trades=  88  WR= 79.5%  PF= 3.46  Sharpe=  5.72  MaxDD= 1.67%  Ret=  13.20%
  iter  31 [grid] trades=  95  WR= 81.1%  PF= 3.21  Sharpe=  5.77  MaxDD= 2.64%  Ret=  18.50%
  iter  32 [grid] trades=  91  WR= 81.3%  PF= 3.90  Sharpe=  6.23  MaxDD= 1.67%  Ret=  13.73%
  iter  33 [grid] trades=  65  WR= 78.5%  PF= 3.83  Sharpe=  5.68  MaxDD= 2.73%  Ret=  15.11%
  iter  34 [grid] trades=  65  WR= 80.0%  PF= 4.83  Sharpe=  6.43  MaxDD= 1.96%  Ret=  12.40%
  iter  35 [grid] trades=  67  WR= 83.6%  PF= 4.02  Sharpe=  5.72  MaxDD= 2.73%  Ret=  15.04%
  iter  36 [grid] trades=  67  WR= 85.1%  PF= 5.13  Sharpe=  6.44  MaxDD= 1.96%  Ret=  12.25%  << TARGETS MET
  iter  37 [refine z_exit=0.2] trades= 105  WR= 81.9%  PF= 4.20  Sharpe=  9.43  MaxDD= 2.64%  Ret=  35.47%
  iter  38 [refine z_exit=0.6000000000000001] trades= 111  WR= 86.5%  PF= 4.38  Sharpe=  9.07  MaxDD= 2.64%  Ret=  29.56%  << TARGETS MET
  iter  39 [refine max_hold=26] trades= 117  WR= 77.8%  PF= 2.66  Sharpe=  7.49  MaxDD= 2.64%  Ret=  24.15%
  iter  40 [refine max_hold=60] trades= 108  WR= 88.0%  PF= 4.23  Sharpe=  9.04  MaxDD= 2.64%  Ret=  28.41%  << TARGETS MET
  BEST (in-sample): trades= 108  WR= 88.0%  PF= 4.23  Sharpe=  9.04  MaxDD= 2.64%  Ret=  28.41%

### VIX-MACRO-MR (Mode 2, Volatility, daily) — optimization log
  iter   1 [grid] trades=  62  WR= 59.7%  PF= 1.08  Sharpe=  0.07  MaxDD= 4.81%  Ret=   2.50%
  iter   2 [grid] trades=  54  WR= 66.7%  PF= 1.52  Sharpe=  0.32  MaxDD= 6.33%  Ret=  20.33%
  iter   3 [grid] trades=  62  WR= 61.3%  PF= 1.05  Sharpe=  0.04  MaxDD= 5.03%  Ret=   0.95%
  iter   4 [grid] trades=  54  WR= 68.5%  PF= 1.50  Sharpe=  0.33  MaxDD= 6.33%  Ret=  19.82%
  iter   5 [grid] trades=  43  WR= 55.8%  PF= 1.39  Sharpe=  0.25  MaxDD=10.91%  Ret=  17.66%
  iter   6 [grid] trades=  39  WR= 66.7%  PF= 1.40  Sharpe=  0.23  MaxDD=13.36%  Ret=  12.94%
  iter   7 [grid] trades=  43  WR= 58.1%  PF= 1.40  Sharpe=  0.27  MaxDD=11.27%  Ret=  17.78%
  iter   8 [grid] trades=  40  WR= 70.0%  PF= 1.52  Sharpe=  0.30  MaxDD=13.36%  Ret=  16.11%
  iter   9 [grid] trades=  31  WR= 58.1%  PF= 1.45  Sharpe=  0.22  MaxDD= 7.41%  Ret=  11.67%
  iter  10 [grid] trades=  28  WR= 64.3%  PF= 1.34  Sharpe=  0.16  MaxDD= 7.36%  Ret=   6.67%
  iter  11 [grid] trades=  32  WR= 68.8%  PF= 1.86  Sharpe=  0.37  MaxDD= 7.41%  Ret=  21.08%
  iter  12 [grid] trades=  29  WR= 75.9%  PF= 1.80  Sharpe=  0.33  MaxDD= 7.36%  Ret=  13.89%
  iter  13 [grid] trades=  49  WR= 61.2%  PF= 1.68  Sharpe=  0.37  MaxDD= 4.94%  Ret=  23.89%
  iter  14 [grid] trades=  43  WR= 67.4%  PF= 1.78  Sharpe=  0.38  MaxDD= 5.70%  Ret=  18.99%
  iter  15 [grid] trades=  49  WR= 63.3%  PF= 1.57  Sharpe=  0.33  MaxDD= 5.28%  Ret=  19.75%
  iter  16 [grid] trades=  43  WR= 69.8%  PF= 1.77  Sharpe=  0.40  MaxDD= 6.03%  Ret=  18.97%
  iter  17 [grid] trades=  33  WR= 54.5%  PF= 0.97  Sharpe= -0.00  MaxDD= 7.02%  Ret=  -0.38%
  iter  18 [grid] trades=  31  WR= 64.5%  PF= 1.03  Sharpe=  0.03  MaxDD= 6.89%  Ret=   0.65%
  iter  19 [grid] trades=  33  WR= 57.6%  PF= 1.35  Sharpe=  0.18  MaxDD= 7.18%  Ret=   8.85%
  iter  20 [grid] trades=  31  WR= 67.7%  PF= 1.20  Sharpe=  0.12  MaxDD= 7.75%  Ret=   4.27%
  iter  21 [grid] trades=  27  WR= 59.3%  PF= 1.34  Sharpe=  0.16  MaxDD= 7.39%  Ret=   7.29%
  iter  22 [grid] trades=  25  WR= 68.0%  PF= 1.35  Sharpe=  0.15  MaxDD= 7.31%  Ret=   5.85%
  iter  23 [grid] trades=  28  WR= 67.9%  PF= 1.56  Sharpe=  0.25  MaxDD= 8.44%  Ret=  11.94%
  iter  24 [grid] trades=  26  WR= 76.9%  PF= 1.74  Sharpe=  0.28  MaxDD= 7.31%  Ret=  10.77%
  iter  25 [grid] trades=  36  WR= 66.7%  PF= 2.79  Sharpe=  0.53  MaxDD= 4.63%  Ret=  25.63%
  iter  26 [grid] trades=  31  WR= 71.0%  PF= 2.37  Sharpe=  0.41  MaxDD= 3.90%  Ret=  13.48%
  iter  27 [grid] trades=  36  WR= 69.4%  PF= 2.70  Sharpe=  0.55  MaxDD= 2.57%  Ret=  24.50%
  iter  28 [grid] trades=  31  WR= 74.2%  PF= 2.35  Sharpe=  0.44  MaxDD= 3.90%  Ret=  13.43%
  iter  29 [grid] trades=  25  WR= 60.0%  PF= 0.99  Sharpe=  0.00  MaxDD= 4.91%  Ret=  -0.13%
  iter  30 [grid] trades=  23  WR= 73.9%  PF= 1.60  Sharpe=  0.20  MaxDD= 6.68%  Ret=   6.22%
  iter  31 [grid] trades=  25  WR= 60.0%  PF= 1.03  Sharpe=  0.02  MaxDD= 3.79%  Ret=   0.25%
  iter  32 [grid] trades=  23  WR= 73.9%  PF= 1.50  Sharpe=  0.17  MaxDD= 6.68%  Ret=   5.10%
  iter  33 [grid] trades=  21  WR= 66.7%  PF= 2.32  Sharpe=  0.31  MaxDD= 7.39%  Ret=  12.60%
  iter  34 [grid] trades=  19  WR= 73.7%  PF= 2.23  Sharpe=  0.27  MaxDD= 6.65%  Ret=   8.39%
  iter  35 [grid] trades=  22  WR= 72.7%  PF= 2.23  Sharpe=  0.31  MaxDD= 7.39%  Ret=  12.46%
  iter  36 [grid] trades=  20  WR= 80.0%  PF= 2.13  Sharpe=  0.27  MaxDD= 6.65%  Ret=   8.42%
  iter  37 [refine z_exit=0.2] trades=  36  WR= 66.7%  PF= 2.79  Sharpe=  0.53  MaxDD= 4.63%  Ret=  25.63%
  iter  38 [refine z_exit=0.6000000000000001] trades=  36  WR= 72.2%  PF= 2.57  Sharpe=  0.54  MaxDD= 2.39%  Ret=  22.29%
  iter  39 [refine max_hold=26] trades=  36  WR= 69.4%  PF= 2.64  Sharpe=  0.55  MaxDD= 2.52%  Ret=  24.62%
  iter  40 [refine max_hold=60] trades=  36  WR= 69.4%  PF= 2.70  Sharpe=  0.55  MaxDD= 2.57%  Ret=  24.50%
  BEST (in-sample): trades=  36  WR= 69.4%  PF= 2.70  Sharpe=  0.55  MaxDD= 2.57%  Ret=  24.50%
```
