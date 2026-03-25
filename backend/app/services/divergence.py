"""
COT Dashboard v2 – Divergence detection engine.
Implements spec section 20.16.

Logic:
  priceTrend = slope(weekly_close_series[-N:])
  cotTrend   = slope(nc_net_series[-N:])

  priceTrend > 0 AND cotTrend < 0 → Bearish divergence
  priceTrend < 0 AND cotTrend > 0 → Bullish divergence

  strength = abs(priceTrend - cotTrend)  (normalised to [0, 1])
"""
import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.config import DIVERGENCE_WINDOW
from app.models import CotDerived, CotPairs
from app.services.price_fetcher import get_recent_weekly_closes

logger = logging.getLogger(__name__)


def _linear_slope(values: list[float]) -> Optional[float]:
    """Return the slope of a simple linear regression over the given series."""
    n = len(values)
    if n < 2:
        return None
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den != 0 else None


def _normalise(slope: float, series: list[float]) -> float:
    """Normalise slope by the mean of the series to make it scale-independent."""
    mean = sum(series) / len(series) if series else 1.0
    return slope / abs(mean) if mean != 0 else slope


def compute_divergence(
    pair: str,
    report_date: date,
    db: Session,
    window: int = DIVERGENCE_WINDOW,
) -> dict:
    """
    Compute divergence for a single pair at a given report_date.

    Returns dict with keys:
      divergence_type     : "Bullish" | "Bearish" | None
      divergence_strength : float (0–1 normalised) | None
      divergence_active   : bool | None
    """
    base  = pair[:3]
    quote = pair[3:]

    # --- COT trend: nc_net slope for base and quote ---
    def get_nc_net_series(currency: str) -> list[float]:
        rows = (
            db.query(CotDerived.report_date, CotDerived.nc_net)
            .filter(CotDerived.currency == currency)
            .filter(CotDerived.nc_net.isnot(None))
            .order_by(CotDerived.report_date.desc())
            .limit(window + 2)
            .all()
        )
        # Filter to only rows <= report_date
        rows = [r for r in rows if r.report_date <= report_date]
        rows = sorted(rows, key=lambda r: r.report_date)[-window:]
        return [float(r.nc_net) for r in rows]

    base_nc  = get_nc_net_series(base)
    quote_nc = get_nc_net_series(quote)

    if len(base_nc) < 2 or len(quote_nc) < 2:
        return {"divergence_type": None, "divergence_strength": None, "divergence_active": None}

    # Pair COT trend: base nc_net minus quote nc_net (normalised)
    min_len  = min(len(base_nc), len(quote_nc))
    pair_cot = [b - q for b, q in zip(base_nc[-min_len:], quote_nc[-min_len:])]
    cot_slope = _linear_slope(pair_cot)

    # --- Price trend ---
    price_closes = get_recent_weekly_closes(pair, report_date, window + 2, db)
    if len(price_closes) < 2:
        return {"divergence_type": None, "divergence_strength": None, "divergence_active": None}

    price_slope = _linear_slope(price_closes[-window:])

    if cot_slope is None or price_slope is None:
        return {"divergence_type": None, "divergence_strength": None, "divergence_active": None}

    # --- Divergence detection (spec 20.16) ---
    if price_slope > 0 and cot_slope < 0:
        div_type = "Bearish"
    elif price_slope < 0 and cot_slope > 0:
        div_type = "Bullish"
    else:
        div_type = None

    if div_type is None:
        return {"divergence_type": None, "divergence_strength": None, "divergence_active": None}

    # Strength = abs difference of normalised slopes
    norm_price = _normalise(price_slope, price_closes[-window:])
    norm_cot   = _normalise(cot_slope, pair_cot[-window:])
    strength   = min(1.0, abs(norm_price - norm_cot))

    return {
        "divergence_type":     div_type,
        "divergence_strength": round(strength, 4),
        "divergence_active":   "true",
    }


def update_pair_divergences(db: Session, report_date: date) -> None:
    """
    Compute and persist divergence for all pairs at the given report_date.
    Skips pairs where price data is unavailable.
    """
    pairs = (
        db.query(CotPairs)
        .filter(CotPairs.report_date == report_date)
        .all()
    )
    updated = 0
    for p in pairs:
        result = compute_divergence(p.pair, report_date, db)
        p.divergence_type     = result["divergence_type"]
        p.divergence_strength = result["divergence_strength"]
        p.divergence_active   = result["divergence_active"]
        updated += 1

    db.commit()
    logger.info("Divergence updated for %d pairs at %s", updated, report_date)
