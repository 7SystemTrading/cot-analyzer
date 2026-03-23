"""
Exhaustion Contrarian -signaalirouter.

Perustuu backtesting-löydökseen:
  Kun parin A-komponentti (positioning z-score erotus) on äärimmäinen (|pair_A| > 3.0)
  JA A edelleen kasvaa verrattuna edelliseen viikkoon,
  seuraavan viikon hintaliike on kontraarinen 57% ajasta (200vk otos, Sharpe ~0.86).

Signaali:
  pair_A > +3.0 ja kasvaa → CONTRARIAN_SHORT (ennusta laskua)
  pair_A < -3.0 ja kasvaa → CONTRARIAN_LONG (ennusta nousua)
"""
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CurrencyMetrics
from app.config import DISPLAY_PAIRS
from app.schemas import ExhaustionDashboardResponse, ExhaustionSignalPair

router = APIRouter(prefix="/api/v1/exhaustion", tags=["exhaustion"])
logger = logging.getLogger(__name__)

# Kynnysarvo: yksittäisen valuutan |z| > tämä = extreme
# Parin erotukselle käytetään 2x tätä (koska pair_A = base_z - quote_z)
DEFAULT_CCY_THRESHOLD = 1.5


def _compute_signals(
    db: Session,
    rd: date,
    ccy_threshold: float = DEFAULT_CCY_THRESHOLD,
) -> tuple[list[ExhaustionSignalPair], list[ExhaustionSignalPair], int]:
    """Laskee Exhaustion Contrarian -signaalit yhdelle viikolle."""

    pair_threshold = ccy_threshold * 2  # Parin erotuksen raja

    # Nykyisen viikon data
    ccy_now = {
        cm.currency: cm
        for cm in db.query(CurrencyMetrics)
        .filter(CurrencyMetrics.report_date == rd)
        .filter(CurrencyMetrics.z_current.isnot(None))
        .all()
    }

    # Edellisen viikon data (A:n kasvun tarkistus)
    prev_rd = rd - timedelta(days=7)
    ccy_prev = {
        cm.currency: cm
        for cm in db.query(CurrencyMetrics)
        .filter(CurrencyMetrics.report_date == prev_rd)
        .filter(CurrencyMetrics.z_current.isnot(None))
        .all()
    }

    contrarian_short = []
    contrarian_long = []
    neutral_count = 0

    for base, quote in DISPLAY_PAIRS:
        base_cm = ccy_now.get(base)
        quote_cm = ccy_now.get(quote)
        if not base_cm or not quote_cm:
            continue

        pair_A = base_cm.z_current - quote_cm.z_current

        # Edellinen viikko
        prev_base = ccy_prev.get(base)
        prev_quote = ccy_prev.get(quote)
        pair_A_prev = None
        a_growing = False

        if prev_base and prev_quote and prev_base.z_current is not None and prev_quote.z_current is not None:
            pair_A_prev = prev_base.z_current - prev_quote.z_current
            # A kasvaa = |pair_A| > |pair_A_prev| JA sama etumerkki
            a_growing = (
                abs(pair_A) > abs(pair_A_prev)
                and pair_A * pair_A_prev > 0
            )

        pair_name = f"{base}{quote}"
        is_extreme = abs(pair_A) > pair_threshold

        if not is_extreme:
            neutral_count += 1
            continue

        # Signaalin vahvuus
        if is_extreme and a_growing:
            strength = "strong"
        elif is_extreme:
            strength = "moderate"
        else:
            strength = "none"

        # Suunta
        if pair_A > 0:
            signal = "CONTRARIAN_SHORT"
            if a_growing:
                note = (
                    f"{base} positioning äärimmäisen pitkä vs {quote} ja edelleen kasvamassa. "
                    f"Exhaustion-riski korkea → kontraarinen short-bias."
                )
            else:
                note = (
                    f"{base} positioning äärimmäisen pitkä vs {quote}, mutta ei enää kasva. "
                    f"Exhaustion mahdollinen mutta momentum hiipumassa."
                )
        else:
            signal = "CONTRARIAN_LONG"
            if a_growing:
                note = (
                    f"{base} positioning äärimmäisen lyhyt vs {quote} ja edelleen syvenemässä. "
                    f"Exhaustion-riski korkea → kontraarinen long-bias."
                )
            else:
                note = (
                    f"{base} positioning äärimmäisen lyhyt vs {quote}, mutta ei enää syvene. "
                    f"Exhaustion mahdollinen mutta momentum hiipumassa."
                )

        row = ExhaustionSignalPair(
            pair=pair_name,
            pair_A=round(pair_A, 3),
            pair_A_prev=round(pair_A_prev, 3) if pair_A_prev is not None else None,
            a_growing=a_growing,
            signal=signal,
            signal_strength=strength,
            note=note,
        )

        if signal == "CONTRARIAN_SHORT":
            contrarian_short.append(row)
        else:
            contrarian_long.append(row)

    # Järjestä vahvuuden mukaan
    contrarian_short.sort(key=lambda s: abs(s.pair_A), reverse=True)
    contrarian_long.sort(key=lambda s: abs(s.pair_A), reverse=True)

    return contrarian_short, contrarian_long, neutral_count


@router.get("", response_model=ExhaustionDashboardResponse)
def get_exhaustion_signals(
    report_date: Optional[str] = Query(None, description="YYYY-MM-DD, oletuksena uusin"),
    threshold: float = Query(DEFAULT_CCY_THRESHOLD, ge=0.5, le=3.0, description="Valuuttakohtainen |z| raja"),
    db: Session = Depends(get_db),
):
    """Palauttaa Exhaustion Contrarian -signaalit valitulle viikolle."""

    if report_date:
        try:
            rd = date.fromisoformat(report_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Virheellinen päivämäärä")
    else:
        latest = (
            db.query(CurrencyMetrics.report_date)
            .filter(CurrencyMetrics.z_current.isnot(None))
            .order_by(CurrencyMetrics.report_date.desc())
            .first()
        )
        if not latest:
            return ExhaustionDashboardResponse()
        rd = latest[0]

    publish_date = rd + timedelta(days=3)
    c_short, c_long, neutral = _compute_signals(db, rd, threshold)

    return ExhaustionDashboardResponse(
        report_date=rd,
        publish_date=publish_date,
        threshold=threshold,
        contrarian_short=c_short,
        contrarian_long=c_long,
        neutral_count=neutral,
    )
