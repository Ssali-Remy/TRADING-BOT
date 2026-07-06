# REAL DATA VALIDATION REPORT

*Generated 2026-07-06 19:25. All series below are REAL market data obtained from datasets bundled inside PyPI packages (skfolio, backtesting) — the only data source this sandbox's network policy allows.*

## Data constraint — read first

**No offline source contains data after 2022-12-28**, so "the past 3 years" cannot be tested from this environment. The most recent real window (2020–2022, reported per book below) includes the COVID crash, the 2020-21 bull run and the 2022 bear market — a demanding out-of-sample stress test. For current data, run `backtest_engine.py` on an unrestricted network (it auto-uses yfinance).

Targets: WR ≥ 85%, PF ≥ 2.5, MaxDD ≤ 10%, Sharpe ≥ 2.0 (from project brief).

---

## REAL-SPX-MACRO — Mode 2 on real S&P 500 daily closes (1990-2022)

Real index closes; OHLC synthesized conservatively (close-only source). Params chosen on pre-2013 data only — everything after is out-of-sample.

| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |
|---|---|---|---|---|---|---|---|
| Train 1990→2013 (optimized) | 52 | 51.9% | 2.32 | 0.49 | 13.99% | 111.61% | 2.14 |
| **OOS 2013→2022 (untouched)** | 27 | 44.4% | 2.68 | 0.57 | 12.92% | 43.73% | 3.34 |
| 2020→2022 slice (most recent real data) | 7 | 57.1% | 0.87 | -0.01 | 5.93% | -0.50% | 0.65 |

**Parameters:** `MacroParams(regime_prob_entry=0.55, regime_prob_exit=0.4, hurst_window=250, hurst_min=0.53, adx_window=14, adx_min=18.0, mom_lookback=126, breakout_lookback=55, atr_window=20, trail_atr=3.5, sl_atr=2.5)`

**Monte Carlo (1000 resamples of OOS trades):** median return 43.8% (5th -2.4%, 95th 118.1%), median MaxDD 8.0%, P(loss) 6%.

**OOS equity curve:**
```
     149,109 |                                                        █       
             |                                                   █████·       
             |                                                 ██······███████
             |                                                █···············
             |                                            ████················
             |                                    █    █  ····················
             |                                ████·████·██····················
             |                                ································
             |                               █································
             |       █ █                  █ █·································
             |███████·█·████            ██·█··································
      89,974 |··············████████████······································
             ----------------------------------------------------------------
```

---

## REAL-GOOG-TRANSFER — SPX-trained params on real GOOG OHLCV (2004-2013), zero tuning

Real daily OHLCV. The parameters were never shown any GOOG data — this is a cross-asset generalization test of the trend logic.

| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |
|---|---|---|---|---|---|---|---|
| GOOG full period (pure transfer) | 19 | 52.6% | 2.84 | 0.72 | 14.22% | 36.28% | 2.56 |

**Parameters:** `MacroParams(regime_prob_entry=0.55, regime_prob_exit=0.4, hurst_window=250, hurst_min=0.53, adx_window=14, adx_min=18.0, mom_lookback=126, breakout_lookback=55, atr_window=20, trail_atr=3.5, sl_atr=2.5)`

**Monte Carlo (1000 resamples of OOS trades):** median return 34.1% (5th -0.6%, 95th 94.3%), median MaxDD 7.0%, P(loss) 5%.

**OOS equity curve:**
```
     136,285 |                                                               █
             |                                                            █  ·
             |                                        ███████             ·  ·
             |                                       █·······█            ·██·
             |                                      █·········████        ····
             |                                      ··············█████   ····
             |                        ██████████████···················  █····
             |                        ·································██·····
             |                        ········································
             |                        ········································
             |                 █   ███········································
      99,355 |█████████████████·███···········································
             ----------------------------------------------------------------
```

---

## REAL-RV-MEANREV — volatility z-score book on realized vol of real S&P returns

⚠️ Realized vol is NOT directly tradeable (no VIX futures data exists offline). This validates the mean-reversion LOGIC on real market dynamics, not an executable P&L.

| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |
|---|---|---|---|---|---|---|---|
| Train (optimized) | 124 | 96.8% | 10.89 | 1.67 | 5.06% | 314.40% | 0.36 |
| **OOS (untouched)** | 49 | 87.8% | 6.62 | 1.24 | 8.96% | 112.36% | 0.92 |
| 2020→2022 slice | 18 | 88.9% | 7.96 | 1.37 | 3.10% | 20.75% | 1.00 |

**Parameters:** `VolParams(z_window=40, z_entry_short=1.5, z_entry_long=-2.0, z_exit=0.5, z_stop=3.2, atr_window=14, sl_atr=4.0, max_hold=40, contango_gate=0.0, vov_window=60, vov_max_pct=0.9, long_size_mult=0.5)`

**Monte Carlo (1000 resamples of OOS trades):** median return 110.8% (5th 68.7%, 95th 164.7%), median MaxDD 3.9%, P(loss) 0%.

**OOS equity curve:**
```
     212,357 |                                                              ██
             |                                                           ███··
             |                                                      █ ███·····
             |                                                     █·█········
             |                                                   ██···········
             |                                               ████·············
             |                                        ███████·················
             |                                 ███████························
             |                            █████·······························
             |                      ██████····································
             |             █████████··········································
     100,000 |█████████████···················································
             ----------------------------------------------------------------
```

---

## REAL-EURUSD-SCALPER — Mode 1 on real EURUSD hourly bars with real tick volume

Real intraday OHLC + tick volume. Hourly grain (minute data does not exist in any offline source).

| Sample | Trades | Win rate | PF | Sharpe | MaxDD | Return | Payoff |
|---|---|---|---|---|---|---|---|
| Train (optimized) | 200 | 50.5% | 0.54 | -1.97 | 4.06% | -3.16% | 0.53 |
| **OOS (untouched)** | 79 | 65.8% | 1.01 | 0.07 | 1.68% | 0.06% | 0.53 |

**Parameters:** `ScalperParams(vwap_band_k=1.5, fade_k=1.4, fade_tp_frac=0.65, cvd_slope_window=12, bb_window=20, bb_k=2.0, squeeze_quantile=0.25, squeeze_lookback=120, rsi_window=14, atr_window=14, tp_atr=2.0, sl_atr=7.0, max_hold=24, open_skip=1, close_skip=1, trend_ma=24)`

**Monte Carlo (1000 resamples of OOS trades):** median return 0.1% (5th -3.8%, 95th 3.0%), median MaxDD 1.8%, P(loss) 48%.

**OOS equity curve:**
```
     101,091 |                                                          ██    
             |                                                         █··    
             |          ██                                             ···█   
             |          ··                                             ····   
             |        ██··                                             ····█  
             |     ███····                                            █·····  
             |    █·······                                            ······  
             |████········                                            ······██
             |············                                           █········
             |············                █                  ██████ █·········
             |············     ███████████·█             ████······█··········
      99,289 |············█████·············█████████████·····················
             ----------------------------------------------------------------
```

---

## Bottom line

These are the bot's first results on genuine market history. Where the synthetic-data numbers were stronger than the real-data numbers, trust the real-data numbers. None of this authorizes live capital: the required path remains full-history current data (unrestricted network) → 3–6 months paper trading → tiny live pilot.

## Appendix — optimization log

```

### REAL-SPX-MACRO (S&P 500 daily 1990-2022) — optimization log (train only)
  iter   1 trades=  81  WR= 48.1%  PF= 1.36  Sharpe=  0.22  MaxDD=13.01%  Ret=  31.83%
  iter   2 trades=  70  WR= 50.0%  PF= 1.63  Sharpe=  0.30  MaxDD=14.21%  Ret=  46.89%
  iter   3 trades=  68  WR= 42.6%  PF= 1.08  Sharpe=  0.06  MaxDD=13.87%  Ret=   3.71%
  iter   4 trades=  58  WR= 46.6%  PF= 1.99  Sharpe=  0.42  MaxDD=16.58%  Ret=  92.62%
  iter   5 trades=  65  WR= 35.4%  PF= 1.01  Sharpe=  0.02  MaxDD=16.60%  Ret=   0.49%
  iter   6 trades=  57  WR= 40.4%  PF= 1.41  Sharpe=  0.23  MaxDD=18.54%  Ret=  36.21%
  iter   7 trades=  80  WR= 47.5%  PF= 1.09  Sharpe=  0.07  MaxDD=14.45%  Ret=   5.30%
  iter   8 trades=  69  WR= 50.7%  PF= 1.57  Sharpe=  0.28  MaxDD=16.65%  Ret=  40.60%
  iter   9 trades=  67  WR= 43.3%  PF= 1.28  Sharpe=  0.15  MaxDD=15.41%  Ret=  11.46%
  iter  10 trades=  57  WR= 47.4%  PF= 1.95  Sharpe=  0.41  MaxDD=18.62%  Ret=  88.53%
  iter  11 trades=  64  WR= 35.9%  PF= 0.95  Sharpe= -0.02  MaxDD=18.09%  Ret=  -1.83%
  iter  12 trades=  56  WR= 41.1%  PF= 1.37  Sharpe=  0.21  MaxDD=19.83%  Ret=  31.72%
  iter  13 trades=  79  WR= 48.1%  PF= 1.31  Sharpe=  0.20  MaxDD=12.78%  Ret=  24.71%
  iter  14 trades=  69  WR= 49.3%  PF= 1.70  Sharpe=  0.34  MaxDD=15.54%  Ret=  56.54%
  iter  15 trades=  66  WR= 43.9%  PF= 1.33  Sharpe=  0.17  MaxDD=14.47%  Ret=  13.60%
  iter  16 trades=  57  WR= 47.4%  PF= 2.00  Sharpe=  0.43  MaxDD=16.58%  Ret=  93.03%
  iter  17 trades=  63  WR= 36.5%  PF= 1.11  Sharpe=  0.07  MaxDD=17.03%  Ret=   3.63%
  iter  18 trades=  56  WR= 41.1%  PF= 1.44  Sharpe=  0.24  MaxDD=19.27%  Ret=  40.41%
  iter  19 trades=  78  WR= 47.4%  PF= 1.02  Sharpe=  0.03  MaxDD=13.80%  Ret=   1.14%
  iter  20 trades=  68  WR= 50.0%  PF= 1.58  Sharpe=  0.30  MaxDD=17.88%  Ret=  45.04%
  iter  21 trades=  65  WR= 44.6%  PF= 1.12  Sharpe=  0.08  MaxDD=16.01%  Ret=   4.70%
  iter  22 trades=  56  WR= 48.2%  PF= 1.96  Sharpe=  0.42  MaxDD=18.59%  Ret=  89.01%
  iter  23 trades=  62  WR= 37.1%  PF= 1.03  Sharpe=  0.03  MaxDD=18.51%  Ret=   0.88%
  iter  24 trades=  55  WR= 41.8%  PF= 1.41  Sharpe=  0.22  MaxDD=20.47%  Ret=  36.06%
  iter  25 trades=  71  WR= 46.5%  PF= 1.66  Sharpe=  0.38  MaxDD=16.68%  Ret=  66.98%
  iter  26 trades=  64  WR= 51.6%  PF= 2.00  Sharpe=  0.45  MaxDD=13.38%  Ret=  82.25%
  iter  27 trades=  58  WR= 46.6%  PF= 1.83  Sharpe=  0.42  MaxDD=17.12%  Ret=  91.15%
  iter  28 trades=  52  WR= 51.9%  PF= 2.32  Sharpe=  0.49  MaxDD=13.99%  Ret= 111.61%
  iter  29 trades=  57  WR= 40.4%  PF= 1.44  Sharpe=  0.26  MaxDD=19.71%  Ret=  47.02%
  iter  30 trades=  51  WR= 45.1%  PF= 1.70  Sharpe=  0.31  MaxDD=17.24%  Ret=  64.54%
  iter  31 trades=  70  WR= 47.1%  PF= 1.64  Sharpe=  0.37  MaxDD=18.15%  Ret=  64.78%
  iter  32 trades=  63  WR= 52.4%  PF= 1.98  Sharpe=  0.44  MaxDD=14.90%  Ret=  79.85%
  iter  33 trades=  57  WR= 47.4%  PF= 1.81  Sharpe=  0.41  MaxDD=18.87%  Ret=  87.73%
  iter  34 trades=  51  WR= 52.9%  PF= 2.28  Sharpe=  0.48  MaxDD=15.65%  Ret= 107.82%
  iter  35 trades=  56  WR= 41.1%  PF= 1.40  Sharpe=  0.24  MaxDD=20.85%  Ret=  41.20%
  iter  36 trades=  50  WR= 46.0%  PF= 1.68  Sharpe=  0.31  MaxDD=19.00%  Ret=  61.57%
  BEST (train): trades=  52  WR= 51.9%  PF= 2.32  Sharpe=  0.49  MaxDD=13.99%  Ret= 111.61%

### REAL-GOOG-TRANSFER
  trades=  19  WR= 52.6%  PF= 2.84  Sharpe=  0.72  MaxDD=14.22%  Ret=  36.28%

### REAL-RV-MEANREV (S&P realized vol 1990-2022) — optimization log (train only)
  iter   1 trades= 129  WR= 86.0%  PF= 6.03  Sharpe=  1.54  MaxDD=10.36%  Ret=3337.29%
  iter   2 trades= 118  WR= 96.6%  PF=10.63  Sharpe=  1.39  MaxDD= 5.69%  Ret= 290.44%
  iter   3 trades= 133  WR= 88.0%  PF= 7.02  Sharpe=  1.77  MaxDD= 8.04%  Ret=4112.56%
  iter   4 trades= 124  WR= 96.8%  PF=10.89  Sharpe=  1.67  MaxDD= 5.06%  Ret= 314.40%
  iter   5 trades= 123  WR= 84.6%  PF= 6.03  Sharpe=  1.52  MaxDD=10.36%  Ret=3052.00%
  iter   6 trades= 113  WR= 94.7%  PF= 8.68  Sharpe=  1.49  MaxDD= 5.69%  Ret= 380.51%
  iter   7 trades= 124  WR= 84.7%  PF= 6.07  Sharpe=  1.57  MaxDD=10.36%  Ret=2902.44%
  iter   8 trades= 114  WR= 94.7%  PF= 8.64  Sharpe=  1.53  MaxDD= 5.69%  Ret= 367.35%
  iter   9 trades= 106  WR= 83.0%  PF= 5.10  Sharpe=  1.43  MaxDD=16.68%  Ret=2288.67%
  iter  10 trades=  97  WR= 90.7%  PF= 5.61  Sharpe=  1.26  MaxDD= 8.78%  Ret= 373.46%
  iter  11 trades= 110  WR= 85.5%  PF= 5.75  Sharpe=  1.64  MaxDD=10.36%  Ret=2749.73%
  iter  12 trades= 103  WR= 93.2%  PF= 7.12  Sharpe=  1.52  MaxDD= 5.69%  Ret= 353.91%
  iter  13 trades=  75  WR= 90.7%  PF= 8.30  Sharpe=  1.14  MaxDD=12.38%  Ret= 469.16%
  iter  14 trades=  72  WR= 97.2%  PF=13.42  Sharpe=  1.16  MaxDD= 4.13%  Ret=  98.60%
  iter  15 trades=  75  WR= 93.3%  PF=11.29  Sharpe=  1.40  MaxDD= 6.32%  Ret= 513.51%
  iter  16 trades=  73  WR= 97.3%  PF=13.10  Sharpe=  1.27  MaxDD= 4.01%  Ret=  95.02%
  iter  17 trades=  79  WR= 93.7%  PF=14.76  Sharpe=  1.37  MaxDD=10.36%  Ret= 896.35%
  iter  18 trades=  77  WR= 98.7%  PF=43.13  Sharpe=  1.38  MaxDD= 2.90%  Ret= 124.27%
  iter  19 trades=  79  WR= 93.7%  PF=14.59  Sharpe=  1.41  MaxDD=10.36%  Ret= 834.51%
  iter  20 trades=  77  WR= 98.7%  PF=42.52  Sharpe=  1.40  MaxDD= 2.90%  Ret= 120.33%
  iter  21 trades=  72  WR= 88.9%  PF= 8.53  Sharpe=  1.24  MaxDD=14.44%  Ret= 791.77%
  iter  22 trades=  66  WR= 97.0%  PF=14.82  Sharpe=  1.19  MaxDD= 4.47%  Ret= 119.53%
  iter  23 trades=  73  WR= 90.4%  PF=10.43  Sharpe=  1.40  MaxDD=10.36%  Ret= 853.11%
  iter  24 trades=  68  WR= 98.5%  PF=40.15  Sharpe=  1.39  MaxDD= 2.90%  Ret= 113.11%
  BEST (train): trades= 124  WR= 96.8%  PF=10.89  Sharpe=  1.67  MaxDD= 5.06%  Ret= 314.40%

### REAL-EURUSD-SCALPER (hourly 2017-2018) — optimization log (train only)
  iter   1 trades= 209  WR= 50.2%  PF= 0.58  Sharpe= -2.85  MaxDD= 5.29%  Ret=  -3.87%
  iter   2 trades= 209  WR= 50.2%  PF= 0.58  Sharpe= -2.85  MaxDD= 5.29%  Ret=  -3.87%
  iter   3 trades= 206  WR= 48.5%  PF= 0.53  Sharpe= -3.12  MaxDD= 5.35%  Ret=  -4.70%
  iter   4 trades= 206  WR= 48.5%  PF= 0.53  Sharpe= -3.12  MaxDD= 5.35%  Ret=  -4.70%
  iter   5 trades= 203  WR= 51.7%  PF= 0.51  Sharpe= -2.71  MaxDD= 3.83%  Ret=  -2.98%
  iter   6 trades= 203  WR= 51.7%  PF= 0.51  Sharpe= -2.71  MaxDD= 3.83%  Ret=  -2.98%
  iter   7 trades= 200  WR= 50.5%  PF= 0.54  Sharpe= -1.97  MaxDD= 4.06%  Ret=  -3.16%
  iter   8 trades= 200  WR= 50.5%  PF= 0.54  Sharpe= -1.97  MaxDD= 4.06%  Ret=  -3.16%
  iter   9 trades= 122  WR= 50.8%  PF= 0.58  Sharpe= -2.41  MaxDD= 4.49%  Ret=  -3.18%
  iter  10 trades= 122  WR= 50.8%  PF= 0.58  Sharpe= -2.41  MaxDD= 4.49%  Ret=  -3.18%
  iter  11 trades= 122  WR= 50.0%  PF= 0.52  Sharpe= -2.66  MaxDD= 4.46%  Ret=  -3.93%
  iter  12 trades= 122  WR= 50.0%  PF= 0.52  Sharpe= -2.66  MaxDD= 4.46%  Ret=  -3.93%
  iter  13 trades= 119  WR= 52.1%  PF= 0.49  Sharpe= -2.47  MaxDD= 3.41%  Ret=  -2.62%
  iter  14 trades= 119  WR= 52.1%  PF= 0.49  Sharpe= -2.47  MaxDD= 3.41%  Ret=  -2.62%
  iter  15 trades= 119  WR= 52.1%  PF= 0.50  Sharpe= -2.40  MaxDD= 3.39%  Ret=  -2.56%
  iter  16 trades= 119  WR= 52.1%  PF= 0.50  Sharpe= -2.40  MaxDD= 3.39%  Ret=  -2.56%
  BEST (train): trades= 200  WR= 50.5%  PF= 0.54  Sharpe= -1.97  MaxDD= 4.06%  Ret=  -3.16%
```
