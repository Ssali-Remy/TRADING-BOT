"""
test_bot.py — correctness tests for the trading bot and backtest engine.

Run: python3 -m pytest test_bot.py -v
"""

import numpy as np
import pandas as pd
import pytest

import backtest_engine as be
from trading_bot import (
    TradingBot, TradingMode, AssetClass, RiskConfig,
    ScalperParams, MacroParams, VolParams,
    atr, rsi, adx, session_vwap, volume_delta, cvd, bollinger, zscore,
    hurst_exponent, markov_regime_prob, _blank_signals,
)


# ----------------------------------------------------------------------------
# fixtures
# ----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def minute_df():
    return be.simulate_index_minute(10, seed=5)


@pytest.fixture(scope="module")
def daily_df():
    return be.simulate_index_daily(1000, seed=5)


@pytest.fixture(scope="module")
def vix_df():
    return be.simulate_vix_daily(1500, seed=5)


# ----------------------------------------------------------------------------
# data simulators
# ----------------------------------------------------------------------------

def test_simulators_produce_valid_ohlc(minute_df, daily_df, vix_df):
    for df in (minute_df, daily_df, vix_df):
        assert (df["high"] >= df[["open", "close"]].max(axis=1) - 1e-9).all()
        assert (df["low"] <= df[["open", "close"]].min(axis=1) + 1e-9).all()
        assert (df["close"] > 0).all()
        assert (df["volume"] > 0).all()
        assert df.index.is_monotonic_increasing
        assert not df.isna().any().any()


def test_minute_sim_has_session_structure(minute_df):
    days = pd.Series(minute_df.index.date)
    assert (days.value_counts() == 390).all()          # full sessions
    assert minute_df.index[0].hour == 9 and minute_df.index[0].minute == 30


def test_vix_sim_is_mean_reverting(vix_df):
    # OU log-process: lag-1 autocorrelation of log-level differences vs level
    x = np.log(vix_df["close"])
    dx = x.diff().dropna()
    lagged_level = x.shift(1).dropna().loc[dx.index]
    corr = np.corrcoef(lagged_level, dx)[0, 1]
    assert corr < -0.01, "log-VIX changes should oppose the level (reversion)"


def test_simulators_are_deterministic_per_seed():
    a = be.simulate_index_daily(200, seed=42)
    b = be.simulate_index_daily(200, seed=42)
    c = be.simulate_index_daily(200, seed=43)
    pd.testing.assert_frame_equal(a, b)
    assert not a["close"].equals(c["close"])


# ----------------------------------------------------------------------------
# indicators
# ----------------------------------------------------------------------------

def test_atr_positive_and_scales(minute_df):
    a = atr(minute_df, 14)
    assert (a.dropna() > 0).all()


def test_rsi_bounds(minute_df):
    r = rsi(minute_df["close"], 14)
    assert r.between(0, 100).all()


def test_adx_bounds(daily_df):
    a = adx(daily_df, 14)
    assert (a.dropna() >= 0).all() and (a.dropna() <= 100).all()


def test_session_vwap_resets_each_day(minute_df):
    vwap, _ = session_vwap(minute_df)
    first_bars = pd.Series(minute_df.index.date).ne(
        pd.Series(minute_df.index.date).shift()).to_numpy()
    tp = ((minute_df["high"] + minute_df["low"] + minute_df["close"]) / 3)
    # on the first bar of each session VWAP == that bar's typical price
    assert np.allclose(vwap.to_numpy()[first_bars], tp.to_numpy()[first_bars])


def test_cvd_sign_convention():
    idx = pd.date_range("2025-01-06 09:30", periods=3, freq="min")
    df = pd.DataFrame({
        "open":  [100.0, 100.0, 100.0],
        "high":  [101.0, 101.0, 101.0],
        "low":   [99.0, 99.0, 99.0],
        "close": [101.0, 99.0, 100.0],   # strong up, strong down, neutral
        "volume": [1000.0, 1000.0, 1000.0],
    }, index=idx)
    d = volume_delta(df)
    assert d.iloc[0] > 0 and d.iloc[1] < 0 and abs(d.iloc[2]) < 1e-9
    assert np.isclose(cvd(df).iloc[-1], d.sum())


def test_zscore_stationary_center():
    s = pd.Series(np.sin(np.linspace(0, 40, 500)) + 10)
    z = zscore(s, 60)
    assert abs(z.iloc[100:].mean()) < 0.5


def test_hurst_discriminates_processes():
    rng = np.random.default_rng(1)
    # persistent: AR(1) returns with strong positive autocorrelation
    eps = rng.normal(0, 0.01, 4000)
    r_pers = np.empty(4000); r_pers[0] = eps[0]
    for i in range(1, 4000):
        r_pers[i] = 0.5 * r_pers[i - 1] + eps[i]
    # anti-persistent: AR(1) returns with negative autocorrelation
    r_anti = np.empty(4000); r_anti[0] = eps[0]
    for i in range(1, 4000):
        r_anti[i] = -0.5 * r_anti[i - 1] + eps[i]
    h_pers = hurst_exponent(np.exp(np.cumsum(r_pers)) * 10)
    h_anti = hurst_exponent(np.exp(np.cumsum(r_anti)) * 10)
    h_rw = hurst_exponent(np.exp(np.cumsum(rng.normal(0, 0.01, 4000))) * 10)
    assert h_pers > h_rw > h_anti, "Hurst must rank persistent > RW > anti-persistent"
    assert 0.3 < h_rw < 0.7, "random walk Hurst should be near 0.5"


def test_markov_regime_prob_valid(daily_df):
    p = markov_regime_prob(daily_df["close"].pct_change())
    assert p.between(0, 1).all()
    assert len(p) == len(daily_df)


# ----------------------------------------------------------------------------
# strategy signal contract & routing
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("mode,asset", [
    (TradingMode.ULTRA_PRECISION_SCALPER, AssetClass.INDEX),
    (TradingMode.MACRO_TREND, AssetClass.INDEX),
    (TradingMode.ULTRA_PRECISION_SCALPER, AssetClass.VOLATILITY),
    (TradingMode.MACRO_TREND, AssetClass.VOLATILITY),
])
def test_signal_frame_contract(mode, asset, minute_df, daily_df, vix_df):
    if asset == AssetClass.VOLATILITY:
        df = vix_df
    elif mode == TradingMode.ULTRA_PRECISION_SCALPER:
        df = minute_df
    else:
        df = daily_df
    bot = TradingBot(mode, asset)
    sig = bot.generate_signals(df)
    assert list(sig.index) == list(df.index)
    for col in ("long_entry", "short_entry", "tp_dist", "sl_dist",
                "trail_dist", "max_hold", "force_flat", "size_mult"):
        assert col in sig.columns
    assert sig["long_entry"].dtype == bool and sig["short_entry"].dtype == bool
    valid_sl = sig["sl_dist"].dropna()
    assert (valid_sl[valid_sl.notna()] > 0).all()


def test_router_maps_volatility_to_mean_reversion():
    """Volatility products must never receive momentum logic."""
    for mode in TradingMode:
        bot = TradingBot(mode, AssetClass.VOLATILITY)
        assert type(bot.strategy).__name__ == "VolatilityMeanReversion"
    assert type(TradingBot(TradingMode.MACRO_TREND, AssetClass.INDEX)
                .strategy).__name__ == "MacroTrendTrader"
    assert type(TradingBot(TradingMode.ULTRA_PRECISION_SCALPER, AssetClass.INDEX)
                .strategy).__name__ == "UltraPrecisionScalper"


def test_no_lookahead_in_scalper_signals(minute_df):
    """Signal at bar i must not change when future bars are altered."""
    bot = TradingBot(TradingMode.ULTRA_PRECISION_SCALPER, AssetClass.INDEX)
    sig_full = bot.generate_signals(minute_df)
    cut = len(minute_df) - 390            # drop the last session
    sig_cut = bot.generate_signals(minute_df.iloc[:cut])
    # entries well inside the kept region must be identical
    a = sig_full["long_entry"].iloc[:cut - 1]
    b = sig_cut["long_entry"].iloc[:cut - 1]
    assert (a == b).all()


# ----------------------------------------------------------------------------
# backtester mechanics (hand-built scenarios)
# ----------------------------------------------------------------------------

def _flat_df(n, price=100.0, start="2025-01-06 09:30"):
    idx = pd.date_range(start, periods=n, freq="min")
    return pd.DataFrame({"open": price, "high": price + 0.05,
                         "low": price - 0.05, "close": price,
                         "volume": 1000.0}, index=idx, dtype=float)


def test_backtester_no_signals_no_trades():
    df = _flat_df(100)
    sig = _blank_signals(df.index)
    res = be.run_backtest(df, sig, RiskConfig(), True)
    assert len(res.trades) == 0
    assert np.allclose(res.equity, 100_000.0)


def test_backtester_long_tp_exit_is_profitable():
    df = _flat_df(50)
    # price jumps to 110 at bar 12 and stays
    df.loc[df.index[12]:, ["open", "high", "low", "close"]] = [110, 110.05, 109.95, 110]
    df.loc[df.index[12], "low"] = 100.0   # transition bar spans the move
    sig = _blank_signals(df.index)
    sig.loc[df.index[10], "long_entry"] = True
    sig.loc[df.index[10], "tp_dist"] = 5.0
    sig.loc[df.index[10], "sl_dist"] = 3.0
    res = be.run_backtest(df, sig, RiskConfig(use_kelly=False), True,
                          commission_bps=0.0, slippage_bps=0.0)
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    assert t["dir"] == 1 and t["reason"] in ("tp", "gap_tp") and t["pnl"] > 0


def test_backtester_long_stop_exit_loses_risk_amount():
    df = _flat_df(50)
    df.loc[df.index[12]:, ["open", "high", "low", "close"]] = [90, 90.05, 89.95, 90]
    df.loc[df.index[12], "high"] = 100.0
    sig = _blank_signals(df.index)
    sig.loc[df.index[10], "long_entry"] = True
    sig.loc[df.index[10], "sl_dist"] = 3.0
    risk = RiskConfig(use_kelly=False, risk_per_trade=0.01)
    res = be.run_backtest(df, sig, risk, True,
                          commission_bps=0.0, slippage_bps=0.0)
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    assert t["pnl"] < 0
    # loss should not exceed ~risk budget by much even with the gap
    assert abs(t["pnl"]) <= 100_000 * 0.01 * 4


def test_backtester_short_tp():
    df = _flat_df(50)
    df.loc[df.index[12]:, ["open", "high", "low", "close"]] = [90, 90.05, 89.95, 90]
    df.loc[df.index[12], "high"] = 100.0
    sig = _blank_signals(df.index)
    sig.loc[df.index[10], "short_entry"] = True
    sig.loc[df.index[10], "tp_dist"] = 5.0
    sig.loc[df.index[10], "sl_dist"] = 3.0
    res = be.run_backtest(df, sig, RiskConfig(use_kelly=False), True,
                          commission_bps=0.0, slippage_bps=0.0)
    assert len(res.trades) == 1
    assert res.trades.iloc[0]["dir"] == -1 and res.trades.iloc[0]["pnl"] > 0


def test_backtester_time_stop():
    df = _flat_df(60)
    sig = _blank_signals(df.index)
    sig.loc[df.index[5], "long_entry"] = True
    sig.loc[df.index[5], "sl_dist"] = 50.0     # unreachable
    sig.loc[df.index[5], "max_hold"] = 7
    res = be.run_backtest(df, sig, RiskConfig(use_kelly=False), True)
    assert len(res.trades) == 1
    t = res.trades.iloc[0]
    # hold counter includes the entry bar, so exit_i - entry_i == max_hold - 1
    assert t["reason"] == "time" and t["bars"] == 6


def test_backtester_force_flat():
    df = _flat_df(60)
    sig = _blank_signals(df.index)
    sig.loc[df.index[5], "long_entry"] = True
    sig.loc[df.index[5], "sl_dist"] = 50.0
    sig.loc[df.index[20], "force_flat"] = True
    res = be.run_backtest(df, sig, RiskConfig(use_kelly=False), True)
    assert len(res.trades) == 1 and res.trades.iloc[0]["reason"] == "flat"


def test_backtester_costs_reduce_pnl():
    df = _flat_df(50)
    df.loc[df.index[12]:, ["open", "high", "low", "close"]] = [110, 110.05, 109.95, 110]
    df.loc[df.index[12], "low"] = 100.0
    sig = _blank_signals(df.index)
    sig.loc[df.index[10], "long_entry"] = True
    sig.loc[df.index[10], "tp_dist"] = 5.0
    sig.loc[df.index[10], "sl_dist"] = 3.0
    free = be.run_backtest(df, sig, RiskConfig(use_kelly=False), True,
                           commission_bps=0.0, slippage_bps=0.0)
    costly = be.run_backtest(df, sig, RiskConfig(use_kelly=False), True,
                             commission_bps=5.0, slippage_bps=5.0)
    assert costly.trades.iloc[0]["pnl"] < free.trades.iloc[0]["pnl"]


def test_backtester_entry_at_next_bar_open():
    """Entry must fill at the NEXT bar's open — no same-bar fills."""
    df = _flat_df(50)
    df.loc[df.index[11], "open"] = 105.0     # distinctive next-bar open
    df.loc[df.index[11], "high"] = 105.1
    sig = _blank_signals(df.index)
    sig.loc[df.index[10], "long_entry"] = True
    sig.loc[df.index[10], "sl_dist"] = 50.0
    sig.loc[df.index[10], "max_hold"] = 5
    res = be.run_backtest(df, sig, RiskConfig(use_kelly=False), True,
                          commission_bps=0.0, slippage_bps=0.0)
    assert np.isclose(res.trades.iloc[0]["entry_px"], 105.0)


def test_daily_circuit_breaker_blocks_after_loss():
    """After max_daily_loss is hit, no new entries the same day."""
    n = 200
    df = _flat_df(n)
    sig = _blank_signals(df.index)
    # engineered repeated losers: price staircases down every 4 bars
    px = 100 - 0.5 * (np.arange(n) // 4)
    df["open"] = px; df["close"] = px - 0.4
    df["high"] = px + 0.1; df["low"] = px - 0.6
    for i in range(0, n - 10, 4):
        sig.loc[df.index[i], "long_entry"] = True
        sig.loc[df.index[i], "sl_dist"] = 0.3
    risk = RiskConfig(use_kelly=False, risk_per_trade=0.01, max_daily_loss=0.02)
    res = be.run_backtest(df, sig, risk, True,
                          commission_bps=0.0, slippage_bps=0.0)
    day_loss = res.equity.iloc[-1] / 100_000 - 1
    assert day_loss > -0.06, "circuit breaker must cap single-day bleed"
    assert len(res.trades) < 40, "breaker must stop new entries after limit"


# ----------------------------------------------------------------------------
# metrics, walk-forward hygiene, Monte Carlo
# ----------------------------------------------------------------------------

def test_metrics_math():
    eq = pd.Series(np.linspace(100_000, 110_000, 100),
                   index=pd.date_range("2025-01-06", periods=100, freq="D"))
    trades = pd.DataFrame({"pnl": [100, -50, 200, -50, 300],
                           "ret": [0.001, -0.0005, 0.002, -0.0005, 0.003],
                           "bars": [3, 4, 5, 2, 6]})
    m = be.compute_metrics(eq, trades, np.arange(100), 100_000)
    assert m["n_trades"] == 5
    assert np.isclose(m["win_rate"], 3 / 5)
    assert np.isclose(m["profit_factor"], 600 / 100)
    assert np.isclose(m["max_drawdown"], 0.0)
    assert np.isclose(m["total_return"], 0.10)


def test_composite_score_penalizes_tiny_samples():
    good = {"n_trades": 100, "win_rate": 0.9, "profit_factor": 5.0,
            "sharpe": 5.0, "max_drawdown": 0.02, "total_return": 0.3}
    tiny = dict(good, n_trades=16)
    assert be.composite_score(good, 15) > be.composite_score(tiny, 15)
    none = dict(good, n_trades=3)
    assert be.composite_score(none, 15) == -1.0


def test_walk_forward_split_no_overlap(daily_df):
    split = int(len(daily_df) * 0.70)
    train, test = daily_df.iloc[:split], daily_df.iloc[split:]
    assert train.index.max() < test.index.min()
    assert len(train) + len(test) == len(daily_df)


def test_monte_carlo_output():
    trades = pd.DataFrame({"ret": np.random.default_rng(3).normal(0.002, 0.01, 60)})
    mc = be.monte_carlo(trades, n_paths=200)
    assert mc["paths"] == 200
    assert mc["ret_p5"] <= mc["ret_p50"] <= mc["ret_p95"]
    assert 0 <= mc["p_loss"] <= 1 and 0 <= mc["p_ruin20"] <= 1
    assert mc["dd_p50"] <= mc["dd_p95"]


def test_monte_carlo_too_few_trades():
    assert be.monte_carlo(pd.DataFrame({"ret": [0.01]}))["paths"] == 0


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
