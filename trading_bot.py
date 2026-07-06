"""
trading_bot.py — Dual-mode quantitative trading bot.

Modes
-----
Mode 1: ULTRA_PRECISION_SCALPER — minute bars, VWAP/CVD/BB-squeeze confluence.
Mode 2: MACRO_TREND            — daily bars, Markov regime + Hurst + ADX + TSMOM.

Asset classes
-------------
INDEX      — trend/momentum logic (SPX/NDX/US30 proxies).
VOLATILITY — z-score mean reversion + contango roll-yield logic (VIX/VXX proxies).

The TradingBot router maps (mode, asset_class) -> strategy and refuses
mismatched logic (e.g. momentum-chasing a volatility product).

Strategies emit per-bar signal frames consumed by backtest_engine.EventBacktester.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field, asdict
from enum import Enum

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ----------------------------------------------------------------------------
# Enums & configs
# ----------------------------------------------------------------------------

class TradingMode(Enum):
    ULTRA_PRECISION_SCALPER = "scalper"
    MACRO_TREND = "macro_trend"


class AssetClass(Enum):
    INDEX = "index"
    VOLATILITY = "volatility"


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.0075     # fixed-fractional risk per trade
    use_kelly: bool = True             # 1/4-Kelly overlay on rolling trades
    kelly_fraction: float = 0.25
    kelly_lookback: int = 50
    kelly_cap_mult: float = 2.0        # Kelly may at most double base risk
    max_daily_loss: float = 0.02       # scalper circuit breaker (fraction of equity)


@dataclass
class ScalperParams:
    vwap_band_k: float = 1.5           # entry pullback distance in VWAP-sigma units
    fade_k: float = 1.8                # deep VWAP-band fade threshold (sigma units)
    fade_tp_frac: float = 0.5          # fade target: fraction of distance to VWAP
    cvd_slope_window: int = 12
    bb_window: int = 20
    bb_k: float = 2.0
    squeeze_quantile: float = 0.25     # bandwidth must have been below this quantile
    squeeze_lookback: int = 240
    rsi_window: int = 14
    atr_window: int = 14
    tp_atr: float = 2.00               # take-profit distance (ATR units)
    sl_atr: float = 5.00               # stop-loss distance (ATR units)
    max_hold: int = 90                 # time stop (bars)
    open_skip: int = 15                # skip first N minutes of session
    close_skip: int = 15               # skip last N minutes
    trend_ma: int = 60                 # micro-trend anchor


@dataclass
class MacroParams:
    regime_prob_entry: float = 0.70    # P(risk-on) needed to trade
    regime_prob_exit: float = 0.40     # kill-switch level
    hurst_window: int = 250
    hurst_min: float = 0.53            # persistence needed for momentum logic
    adx_window: int = 14
    adx_min: float = 18.0
    mom_lookback: int = 126            # ~6-month time-series momentum
    breakout_lookback: int = 55        # entry trigger: N-day high breakout
    atr_window: int = 20
    trail_atr: float = 3.5             # chandelier trail width
    sl_atr: float = 2.5                # initial stop


@dataclass
class VolParams:
    z_window: int = 60
    z_entry_short: float = 1.8         # fade spikes above this z
    z_entry_long: float = -2.0         # fade complacency below this z
    z_exit: float = 0.25               # mean-touch exit
    z_stop: float = 3.2                # hard stop in z units
    atr_window: int = 14
    sl_atr: float = 2.0
    max_hold: int = 40
    contango_gate: float = 0.0         # basis > gate required for new shorts
    vov_window: int = 60               # vol-of-vol window
    vov_max_pct: float = 0.90          # no short-vol entries above this vov pctile
    long_size_mult: float = 0.5        # long-vol trades run half size


# ----------------------------------------------------------------------------
# Indicator library (vectorized, no external TA deps)
# ----------------------------------------------------------------------------

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1.0 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1.0 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l = df["high"], df["low"]
    up, dn = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = atr(df, n)
    pdi = 100 * plus_dm.ewm(alpha=1.0 / n, adjust=False).mean() / tr
    mdi = 100 * minus_dm.ewm(alpha=1.0 / n, adjust=False).mean() / tr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1.0 / n, adjust=False).mean().fillna(0.0)


def session_vwap(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Session-anchored VWAP and volume-weighted sigma band width."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    day = pd.Series(df.index.date, index=df.index)
    grp = day.ne(day.shift()).cumsum()
    pv = (tp * df["volume"]).groupby(grp).cumsum()
    vv = df["volume"].groupby(grp).cumsum().replace(0, np.nan)
    vwap = pv / vv
    dev2 = ((tp - vwap) ** 2 * df["volume"]).groupby(grp).cumsum() / vv
    return vwap, np.sqrt(dev2).replace(0, np.nan)


def volume_delta(df: pd.DataFrame) -> pd.Series:
    """Signed volume proxy: body fraction of range times volume."""
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    frac = ((df["close"] - df["open"]) / rng).clip(-1, 1).fillna(0.0)
    return frac * df["volume"]


def cvd(df: pd.DataFrame) -> pd.Series:
    """Cumulative volume delta, session-anchored."""
    day = pd.Series(df.index.date, index=df.index)
    grp = day.ne(day.shift()).cumsum()
    return volume_delta(df).groupby(grp).cumsum()


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std()
    return mid, mid + k * sd, mid - k * sd, (2 * k * sd) / mid  # mid, up, lo, bandwidth


def zscore(series: pd.Series, n: int) -> pd.Series:
    m = series.rolling(n).mean()
    s = series.rolling(n).std().replace(0, np.nan)
    return ((series - m) / s).fillna(0.0)


def hurst_exponent(series: np.ndarray) -> float:
    """R/S estimate of the Hurst exponent on one window of prices."""
    x = np.diff(np.log(np.asarray(series, dtype=float)))
    if len(x) < 32 or np.all(x == 0):
        return 0.5
    ns, rs = [], []
    for n in (16, 32, 64, 128):
        if len(x) < n * 2:
            continue
        chunks = len(x) // n
        vals = []
        for i in range(chunks):
            seg = x[i * n:(i + 1) * n]
            dev = np.cumsum(seg - seg.mean())
            r = dev.max() - dev.min()
            s = seg.std(ddof=1)
            if s > 0:
                vals.append(r / s)
        if vals:
            ns.append(n)
            rs.append(np.mean(vals))
    if len(ns) < 2:
        return 0.5
    h = np.polyfit(np.log(ns), np.log(rs), 1)[0]
    return float(np.clip(h, 0.0, 1.0))


def rolling_hurst(close: pd.Series, window: int = 250, step: int = 10) -> pd.Series:
    """Rolling Hurst, computed every `step` bars and forward-filled."""
    out = pd.Series(np.nan, index=close.index)
    vals = close.to_numpy()
    for i in range(window, len(vals), step):
        out.iloc[i] = hurst_exponent(vals[i - window:i])
    return out.ffill().fillna(0.5)


def markov_regime_prob(returns: pd.Series) -> pd.Series:
    """Filtered P(risk-on) from a 2-state Markov switching model.

    Filtered (not smoothed) probabilities are used to avoid lookahead:
    P(state_t | data up to t). Risk-on = the regime with the lower variance.
    Falls back to a realized-vol percentile proxy if MLE fails to converge.
    """
    r = returns.dropna()
    try:
        from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
        model = MarkovRegression(r.values, k_regimes=2, trend="c", switching_variance=True)
        res = model.fit(em_iter=10, search_reps=5, disp=False)
        variances = [res.params[-2], res.params[-1]]  # sigma2[0], sigma2[1]
        calm = int(np.argmin(variances))
        prob = pd.Series(res.filtered_marginal_probabilities[:, calm], index=r.index)
    except Exception:
        vol = r.rolling(21).std()
        pct = vol.rolling(252, min_periods=63).rank(pct=True)
        prob = (1.0 - pct).fillna(0.5)
    return prob.reindex(returns.index).ffill().fillna(0.5)


# ----------------------------------------------------------------------------
# Signal frame contract
# ----------------------------------------------------------------------------
# Strategies return a DataFrame aligned to the input index with columns:
#   long_entry, short_entry : bool
#   tp_dist, sl_dist        : float, price distance for target/stop (NaN = none)
#   trail_dist              : float, trailing stop distance (NaN = no trail)
#   max_hold                : int bars (0 = unlimited)
#   force_flat              : bool, close any open position on this bar
#   size_mult               : float, per-signal position size multiplier
# ----------------------------------------------------------------------------

def _blank_signals(index: pd.Index) -> pd.DataFrame:
    return pd.DataFrame({
        "long_entry": False, "short_entry": False,
        "tp_dist": np.nan, "sl_dist": np.nan, "trail_dist": np.nan,
        "max_hold": 0, "force_flat": False, "size_mult": 1.0,
    }, index=index)


# ----------------------------------------------------------------------------
# Strategies
# ----------------------------------------------------------------------------

class UltraPrecisionScalper:
    """Mode 1 for INDEX assets: VWAP pullback + CVD confirmation + BB-squeeze release."""

    def __init__(self, params: ScalperParams | None = None):
        self.p = params or ScalperParams()

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.p
        sig = _blank_signals(df.index)
        close = df["close"]

        vwap, vsig = session_vwap(df)
        cvd_s = cvd(df)
        cvd_slope = cvd_s.diff(p.cvd_slope_window)
        _, bb_up, bb_lo, bw = bollinger(close, p.bb_window, p.bb_k)
        squeeze_thr = bw.rolling(p.squeeze_lookback, min_periods=p.bb_window * 2)\
                        .quantile(p.squeeze_quantile)
        was_squeezed = (bw.shift(1) <= squeeze_thr.shift(1)).rolling(5).max() > 0
        rsi_s = rsi(close, p.rsi_window)
        atr_s = atr(df, p.atr_window)
        micro_trend = close.rolling(p.trend_ma).mean()

        # time-of-day mask
        minutes = df.index.hour * 60 + df.index.minute
        day = pd.Series(df.index.date, index=df.index)
        grp = day.ne(day.shift()).cumsum()
        bar_in_day = grp.groupby(grp).cumcount()
        bars_per_day = grp.map(grp.value_counts())
        tod_ok = (bar_in_day >= p.open_skip) & (bar_in_day < bars_per_day - p.close_skip)
        last_bar = bar_in_day >= bars_per_day - 2

        dist = (close - vwap) / vsig

        # Family A — trend-side pullback-reclaim: uptrend side of VWAP, pullback
        # into the VWAP zone, buyers stepping in, recent squeeze resolving.
        long_pb = (
            (close > micro_trend)
            & (dist.shift(1) <= -0.2) & (dist > dist.shift(1))          # pullback then reclaim
            & (dist > -p.vwap_band_k)                                    # not a breakdown
            & (cvd_slope > 0)                                            # buy pressure
            & was_squeezed & (close > bb_lo)                             # compression release
            & (rsi_s > 40) & (rsi_s < 70)
        )
        short_pb = (
            (close < micro_trend)
            & (dist.shift(1) >= 0.2) & (dist < dist.shift(1))
            & (dist < p.vwap_band_k)
            & (cvd_slope < 0)
            & was_squeezed & (close < bb_up)
            & (rsi_s < 60) & (rsi_s > 30)
        )

        # Family B — deep VWAP-band fade: price stretched fade_k sigmas from
        # VWAP and turning back, order flow (CVD) confirming the reversal.
        # Harvests intraday VWAP magnetism; target is the trip back to VWAP.
        long_fd = (
            (dist <= -p.fade_k) & (dist > dist.shift(1))
            & (cvd_slope > cvd_slope.shift(1))                           # selling exhausting
            & (rsi_s < 45)
        )
        short_fd = (
            (dist >= p.fade_k) & (dist < dist.shift(1))
            & (cvd_slope < cvd_slope.shift(1))
            & (rsi_s > 55)
        )

        long_e = (long_pb | long_fd) & tod_ok
        short_e = (short_pb | short_fd) & tod_ok
        is_fade = (long_fd | short_fd) & ~(long_pb | short_pb)

        base_tp = p.tp_atr * atr_s
        fade_tp = np.maximum((close - vwap).abs() * p.fade_tp_frac, 0.5 * atr_s)
        sig["long_entry"] = long_e.fillna(False)
        sig["short_entry"] = short_e.fillna(False)
        sig["tp_dist"] = np.where(is_fade.fillna(False), fade_tp, base_tp)
        sig["sl_dist"] = p.sl_atr * atr_s
        sig["max_hold"] = p.max_hold
        sig["force_flat"] = last_bar.values
        return sig


class MacroTrendTrader:
    """Mode 2 for INDEX assets: regime + Hurst + ADX gated TSMOM breakout, long-only."""

    def __init__(self, params: MacroParams | None = None):
        self.p = params or MacroParams()

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.p
        sig = _blank_signals(df.index)
        close = df["close"]
        rets = close.pct_change()

        # Accept precomputed regime/hurst columns (parameter search caches them —
        # neither depends on the tunable params).
        prob_on = df["regime_prob"] if "regime_prob" in df.columns \
            else markov_regime_prob(rets)
        hurst = df["hurst"] if "hurst" in df.columns \
            else rolling_hurst(close, p.hurst_window)
        adx_s = adx(df, p.adx_window)
        atr_s = atr(df, p.atr_window)
        mom = close.pct_change(p.mom_lookback)
        breakout = close >= close.rolling(p.breakout_lookback).max().shift(1)

        long_e = (
            (prob_on > p.regime_prob_entry)
            & (hurst > p.hurst_min)
            & (adx_s > p.adx_min)
            & (mom > 0)
            & breakout
        )

        sig["long_entry"] = long_e.fillna(False)
        sig["sl_dist"] = p.sl_atr * atr_s
        sig["trail_dist"] = p.trail_atr * atr_s
        sig["force_flat"] = (prob_on < p.regime_prob_exit).fillna(False)
        return sig


class VolatilityMeanReversion:
    """Volatility book: z-score fades + contango gate + vol-of-vol spike overlay.

    Works on VIX-like (spot, mean-reverting) and VXX-like (ETP with roll drag)
    series. Requires optional df['basis'] column (front-month basis; >0 = contango).
    """

    def __init__(self, params: VolParams | None = None, scalper_grain: bool = False):
        self.p = params or VolParams()
        self.scalper_grain = scalper_grain  # minute-level: tighter holds

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.p
        sig = _blank_signals(df.index)
        close = df["close"]

        z = zscore(np.log(close), p.z_window)
        atr_s = atr(df, p.atr_window)
        rets = close.pct_change()
        vov = rets.rolling(p.vov_window).std()
        vov_pct = vov.rolling(max(252, p.vov_window * 4), min_periods=p.vov_window)\
                     .rank(pct=True).fillna(0.5)
        basis = df["basis"] if "basis" in df.columns else pd.Series(0.05, index=df.index)

        # SHORT VOL: spike fade — z above threshold and now rolling over,
        # contango intact, vol-of-vol not in the danger decile.
        short_e = (
            (z > p.z_entry_short)
            & (z < z.shift(1))                       # rollover confirmation
            & (basis > p.contango_gate)
            & (vov_pct < p.vov_max_pct)
        )

        # LONG VOL: complacency fade — z deeply negative and turning up. Half size.
        long_e = (z < p.z_entry_long) & (z > z.shift(1))

        # Minute grain: hold window and stop distance must cover the reversion
        # half-life measured in minutes — hold 6x longer, and the stop scales
        # with sqrt(holding time) so per-minute noise can't shake the trade out.
        if self.scalper_grain:
            max_hold = p.max_hold * 6
            sl_dist = p.sl_atr * 8.0 * atr_s
        else:
            max_hold = p.max_hold
            sl_dist = p.sl_atr * atr_s

        sig["short_entry"] = short_e.fillna(False)
        sig["long_entry"] = long_e.fillna(False)
        sig["sl_dist"] = sl_dist
        sig["max_hold"] = max_hold
        sig["size_mult"] = np.where(long_e, p.long_size_mult, 1.0)
        # mean-touch exit: force flat when z crosses back through ~0
        crossed = (z.abs() < p.z_exit)
        sig["force_flat"] = crossed.fillna(False)
        return sig


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------

class TradingBot:
    """Maps (mode, asset_class) to the correct strategy; guards against
    applying momentum logic to mean-reverting products and vice versa."""

    def __init__(self,
                 mode: TradingMode,
                 asset_class: AssetClass,
                 scalper_params: ScalperParams | None = None,
                 macro_params: MacroParams | None = None,
                 vol_params: VolParams | None = None,
                 risk: RiskConfig | None = None):
        self.mode = mode
        self.asset_class = asset_class
        self.risk = risk or RiskConfig()

        if asset_class == AssetClass.VOLATILITY:
            # Volatility products are mean-reverting: both modes route to the
            # z-score book; mode only changes the holding grain.
            self.strategy = VolatilityMeanReversion(
                vol_params, scalper_grain=(mode == TradingMode.ULTRA_PRECISION_SCALPER))
        elif mode == TradingMode.ULTRA_PRECISION_SCALPER:
            self.strategy = UltraPrecisionScalper(scalper_params)
        else:
            self.strategy = MacroTrendTrader(macro_params)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.strategy.generate(df)

    def describe(self) -> dict:
        return {
            "mode": self.mode.value,
            "asset_class": self.asset_class.value,
            "strategy": type(self.strategy).__name__,
            "params": asdict(self.strategy.p),
            "risk": asdict(self.risk),
        }
