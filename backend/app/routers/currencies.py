from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CurrencyMetrics
from app.schemas import CurrencyMetricsOut

router = APIRouter(prefix="/api/v1/currencies", tags=["currencies"])


@router.get("/ranking", response_model=List[CurrencyMetricsOut])
def get_currency_ranking(
    report_date: Optional[str] = Query(None, description="YYYY-MM-DD, oletuksena uusin"),
    db: Session = Depends(get_db),
):
    """Palauttaa kaikkien valuuttojen rankingin yhdeltä viikolta."""
    if report_date:
        from datetime import date
        try:
            rd = date.fromisoformat(report_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Virheellinen päivämäärä, käytä YYYY-MM-DD")
    else:
        latest = (
            db.query(CurrencyMetrics.report_date)
            .filter(CurrencyMetrics.currency_score.isnot(None))
            .order_by(CurrencyMetrics.report_date.desc())
            .first()
        )
        if not latest:
            return []
        rd = latest[0]

    rows = (
        db.query(CurrencyMetrics)
        .filter(CurrencyMetrics.report_date == rd)
        .filter(CurrencyMetrics.currency_score.isnot(None))
        .order_by(CurrencyMetrics.currency_score.desc())
        .all()
    )
    return [CurrencyMetricsOut.model_validate(r) for r in rows]


@router.get("/{currency}/history", response_model=List[CurrencyMetricsOut])
def get_currency_history(
    currency: str,
    weeks: int = Query(52, ge=1, le=260),
    db: Session = Depends(get_db),
):
    """Palauttaa yksittäisen valuutan historian viimeisiltä N viikolta."""
    currency = currency.upper()
    rows = (
        db.query(CurrencyMetrics)
        .filter(CurrencyMetrics.currency == currency)
        .filter(CurrencyMetrics.currency_score.isnot(None))
        .order_by(CurrencyMetrics.report_date.desc())
        .limit(weeks)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Ei dataa valuutalle {currency}")
    return [CurrencyMetricsOut.model_validate(r) for r in reversed(rows)]


@router.get("/dates", response_model=List[str])
def get_available_dates(db: Session = Depends(get_db)):
    """Palauttaa kaikki saatavilla olevat raporttipäivät."""
    rows = (
        db.query(CurrencyMetrics.report_date)
        .filter(CurrencyMetrics.currency_score.isnot(None))
        .distinct()
        .order_by(CurrencyMetrics.report_date.desc())
        .all()
    )
    return [r[0].isoformat() for r in rows]
