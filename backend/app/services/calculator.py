"""
COT Dashboard v2 – Scoring engine.
Implements spec formulas 20.1–20.15.
"""
import logging
import math
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.config import (
    CURRENCY_BIAS_LEVELS,
    CONVICTION_LEVELS,
    DISPLAY_PAIRS,
    EXTREME_THRESHOLDS,
    PAIR_BIAS_LEVELS,
    PERCENTILE_WINDOW,
    REVERSAL_RISK_LEVELS,
    SCORE_WEIGHTS,
    ScoreWeights,
)
from app.models import AppSettings, CotDerived, CotPairs, CotRaw

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _classify(value: float, levels: list) -> str:
    """
    Walk levels list of (min_score, label).
    Return label for the first entry where value >= min_score.
    Last entry's min_score may be None (catch-all).
    """
    for min_score, label in levels:
        if min_score is None or value >= min_score:
            return label
    return levels[-1][1]


def _extreme_score(percentile: float) -> int:
    """Spec 20.6: convert percentile to extreme score 0–3."""
    for threshold, score in EXTREME_THRESHOLDS:
        if percentile >= threshold:
            return score
    return 0


def _reversal_risk_label(reversal_score: int) -> str:
    """Spec 20.12: convert reversal score to Low/Medium/High."""
    for min_score, label in REVERSAL_RISK_LEVELS:
        if reversal_score >= min_score:
            return label
    return "Low"


def _conviction_label(conviction_score: float) -> str:
    """Spec 20.15: convert conviction score to Low/Medium/High."""
    for min_score, label in CONVICTION_LEVELS:
        if conviction_score >= min_score:
            return label
    return "Low"


# ---------------------------------------------------------------------------
# Per-currency calculation over historical series
# ---------------------------------------------------------------------------

def _calculate_currency_metrics(
    history: pd.DataFrame,
    window: int = PERCENTILE_WINDOW,
    weights=None,
    extreme_thresholds=None,
) -> pd.DataFrame:
    """
    Given a DataFrame of one currency's raw data (sorted by report_date),
    compute all derived metrics for every row.

    Input columns: report_date, nc_long, nc_short, comm_long, comm_short,
                   nr_long, nr_short, open_interest

    Returns DataFrame with all computed columns.
    """
    df = history.copy().sort_values("report_date").reset_index(drop=True)

    # 20.1 Net positions
    df["nc_net"]   = df["nc_long"]   - df["nc_short"]
    df["comm_net"] = df["comm_long"] - df["comm_short"]
    df["nr_net"]   = df["nr_long"]   - df["nr_short"]

    # 20.2 Weekly changes
    df["net_change"] = df["nc_net"].diff()
    df["oi_change"]  = df["open_interest"].diff()

    # 20.3 Net percent of OI
    df["net_pct_oi"] = df["nc_net"] / df["open_interest"].replace(0, float("nan"))

    # 20.4 Percentile over rolling window (lookback – excludes current row)
    def rolling_percentile(series: pd.Series, win: int) -> pd.Series:
        result = pd.Series(index=series.index, dtype=float)
        for i in range(len(series)):
            if i < 2:
                result.iloc[i] = float("nan")
                continue
            start = max(0, i - win)
            window_vals = series.iloc[start:i]  # excludes current (lookback)
            current = series.iloc[i]
            if window_vals.isna().all():
                result.iloc[i] = float("nan")
                continue
            valid = window_vals.dropna()
            if len(valid) == 0:
                result.iloc[i] = float("nan")
                continue
            pct = (valid < current).sum() / len(valid)
            result.iloc[i] = pct
        return result

    df["percentile"] = rolling_percentile(df["net_pct_oi"], window)

    # 20.5 Z-score
    def rolling_zscore(series: pd.Series, win: int) -> pd.Series:
        shifted = series.shift(1)
        mu  = shifted.rolling(win, min_periods=10).mean()
        std = shifted.rolling(win, min_periods=10).std()
        return (series - mu) / std.replace(0, float("nan"))

    df["z_score"] = rolling_zscore(df["net_pct_oi"], window)

    # 20.7 Direction score
    df["dir_score"] = df["nc_net"].apply(
        lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
    )

    # 20.8 Momentum score
    df["mom_score"] = df["net_change"].apply(
        lambda x: 1 if x > 0 else (-1 if x < 0 else 0) if pd.notna(x) else float("nan")
    )

    # 20.9 Strength score
    df["strength_score"] = df.apply(
        lambda r: r["percentile"] * r["dir_score"]
        if pd.notna(r["percentile"]) else float("nan"),
        axis=1,
    )

    # 20.10 Composite currency score [-2, +2]
    w = weights if weights is not None else SCORE_WEIGHTS
    def compute_score(r):
        if pd.isna(r["strength_score"]) or pd.isna(r["mom_score"]):
            return float("nan")
        raw = w.direction * r["dir_score"] + w.momentum * r["mom_score"] + w.strength * r["strength_score"]
        return max(-2.0, min(2.0, raw))

    df["currency_score"] = df.apply(compute_score, axis=1)

    # Bias label
    df["bias_label"] = df["currency_score"].apply(
        lambda s: _classify(s, CURRENCY_BIAS_LEVELS) if pd.notna(s) else None
    )

    # 20.6 Extreme score (uses abs percentile relative to 50%)
    # Spec uses directional percentile: >50% = long-biased extreme, <50% = short-biased extreme
    _thresholds = extreme_thresholds if extreme_thresholds is not None else EXTREME_THRESHOLDS

    def get_extreme(r):
        p = r["percentile"]
        if pd.isna(p):
            return None
        dist = abs(p - 0.5) * 2  # 0–1, distance from neutral
        effective_pct = 0.5 + dist / 2  # map back to 0.5–1.0
        for threshold, score in _thresholds:
            if effective_pct >= threshold:
                return score
        return 0

    df["extreme_score"] = df.apply(get_extreme, axis=1)

    # 20.12 Commercial opposition and reversal risk
    def commercial_opposition(r):
        if pd.isna(r["nc_net"]) or pd.isna(r["comm_net"]):
            return None
        nc_pos  = 1 if r["nc_net"] > 0 else -1
        com_pos = 1 if r["comm_net"] > 0 else -1
        return 1 if nc_pos != com_pos else 0

    df["commercial_opposition"] = df.apply(commercial_opposition, axis=1)

    def reversal_score(r):
        e = r["extreme_score"]
        c = r["commercial_opposition"]
        if pd.isna(e) or pd.isna(c):
            return None
        return int(e) + int(c)

    df["reversal_score"] = df.apply(reversal_score, axis=1)
    df["reversal_risk"]  = df["reversal_score"].apply(
        lambda s: _reversal_risk_label(s) if s is not None else None
    )

    return df


# ---------------------------------------------------------------------------
# Full recalculation (all currencies + all pairs)
# ---------------------------------------------------------------------------

def _load_settings(db: Session):
    """Load runtime settings from DB, falling back to config.py defaults."""
    row = db.query(AppSettings).first()
    if not row:
        return PERCENTILE_WINDOW, SCORE_WEIGHTS, EXTREME_THRESHOLDS
    window = row.percentile_window or PERCENTILE_WINDOW
    weights = ScoreWeights(
        direction=row.weight_direction,
        momentum=row.weight_momentum,
        strength=row.weight_strength,
    )
    thresholds = [
        (row.extreme_threshold_historic, 3),
        (row.extreme_threshold_major,    2),
        (row.extreme_threshold_mild,     1),
        (0.0,                            0),
    ]
    return window, weights, thresholds


def recalculate_all(db: Session) -> None:
    """Recompute CotDerived and CotPairs from scratch using all CotRaw data."""
    logger.info("Starting full recalculation...")

    window, weights, thresholds = _load_settings(db)
    logger.info("Settings: window=%d, weights=%s", window, weights)

    currencies = [r[0] for r in db.query(CotRaw.currency).distinct().all()]
    derived_by_ccy: dict[str, pd.DataFrame] = {}

    for ccy in currencies:
        rows = (
            db.query(CotRaw)
            .filter(CotRaw.currency == ccy)
            .order_by(CotRaw.report_date)
            .all()
        )
        if not rows:
            continue

        hist = pd.DataFrame([{
            "report_date":  r.report_date,
            "nc_long":      r.nc_long,
            "nc_short":     r.nc_short,
            "comm_long":    r.comm_long,
            "comm_short":   r.comm_short,
            "nr_long":      r.nr_long,
            "nr_short":     r.nr_short,
            "open_interest": r.open_interest,
        } for r in rows])

        computed = _calculate_currency_metrics(hist, window=window, weights=weights, extreme_thresholds=thresholds)
        derived_by_ccy[ccy] = computed

        # Upsert CotDerived
        for _, row in computed.iterrows():
            rd = row["report_date"]
            existing = (
                db.query(CotDerived)
                .filter(CotDerived.report_date == rd, CotDerived.currency == ccy)
                .first()
            )

            def _f(val):
                return float(val) if pd.notna(val) else None

            def _i(val):
                return int(val) if val is not None and not pd.isna(val) else None

            values = dict(
                nc_net=_f(row["nc_net"]), comm_net=_f(row["comm_net"]),
                nr_net=_f(row["nr_net"]),
                net_change=_f(row["net_change"]), oi_change=_f(row["oi_change"]),
                net_pct_oi=_f(row["net_pct_oi"]),
                percentile=_f(row["percentile"]), z_score=_f(row["z_score"]),
                dir_score=_f(row["dir_score"]), mom_score=_f(row["mom_score"]),
                strength_score=_f(row["strength_score"]),
                currency_score=_f(row["currency_score"]),
                bias_label=row["bias_label"],
                extreme_score=_i(row["extreme_score"]),
                commercial_opposition=_i(row["commercial_opposition"]),
                reversal_score=_i(row["reversal_score"]),
                reversal_risk=row["reversal_risk"],
            )

            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
            else:
                db.add(CotDerived(report_date=rd, currency=ccy, **values))

        db.commit()
        logger.info("Recalculated %s: %d weeks", ccy, len(computed))

    # Pair metrics
    _recalculate_pairs(db, derived_by_ccy)
    logger.info("Recalculation complete.")


def _recalculate_pairs(db: Session, derived_by_ccy: dict[str, pd.DataFrame]) -> None:
    """Compute CotPairs from derived currency data."""
    if not derived_by_ccy:
        return

    # Get all report dates that have data for at least 2 currencies
    all_dates: set[date] = set()
    for df in derived_by_ccy.values():
        all_dates.update(df["report_date"].tolist())

    for rd in sorted(all_dates):
        for base, quote in DISPLAY_PAIRS:
            base_df  = derived_by_ccy.get(base)
            quote_df = derived_by_ccy.get(quote)
            if base_df is None or quote_df is None:
                continue

            base_row  = base_df[base_df["report_date"] == rd]
            quote_row = quote_df[quote_df["report_date"] == rd]
            if base_row.empty or quote_row.empty:
                continue

            b = base_row.iloc[0]
            q = quote_row.iloc[0]

            if pd.isna(b["currency_score"]) or pd.isna(q["currency_score"]):
                continue

            base_score  = float(b["currency_score"])
            quote_score = float(q["currency_score"])

            # 20.13 Pair score [-4, +4]
            pair_score = max(-4.0, min(4.0, base_score - quote_score))
            pair_label = _classify(pair_score, PAIR_BIAS_LEVELS)

            # 20.15 Conviction
            base_rr  = b["reversal_risk"]
            quote_rr = q["reversal_risk"]
            high_reversal = base_rr == "High" or quote_rr == "High"
            conviction_score = abs(pair_score) - (1 if high_reversal else 0)
            conviction_score = max(0.0, conviction_score)
            conviction = _conviction_label(conviction_score)

            pair_name = f"{base}{quote}"
            existing  = (
                db.query(CotPairs)
                .filter(CotPairs.report_date == rd, CotPairs.pair == pair_name)
                .first()
            )

            values = dict(
                base_currency=base, quote_currency=quote,
                base_score=base_score, quote_score=quote_score,
                pair_score=pair_score, pair_label=pair_label,
                conviction_score=conviction_score, conviction=conviction,
            )

            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
            else:
                db.add(CotPairs(report_date=rd, pair=pair_name, **values))

    db.commit()
    logger.info("Pair metrics written for %d dates", len(all_dates))
