"""
GET /api/v1/currencies           – all currencies for a week
GET /api/v1/currencies/{symbol}  – single currency with history
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CotDerived
from app.schemas import (
    CurrenciesResponse,
    CurrencyBiasItem,
    CurrencyDetailResponse,
    CurrencyHistoryPoint,
)
from app.services.commentary import currency_explanation

router = APIRouter(prefix="/api/v1/currencies", tags=["currencies"])


def _available_dates(db: Session) -> list[date]:
    rows = (
        db.query(CotDerived.report_date)
        .filter(CotDerived.currency_score.isnot(None))
        .distinct()
        .order_by(CotDerived.report_date.desc())
        .all()
    )
    return [r[0] for r in rows]


def _latest_date(db: Session) -> Optional[date]:
    result = (
        db.query(CotDerived.report_date)
        .filter(CotDerived.currency_score.isnot(None))
        .order_by(CotDerived.report_date.desc())
        .first()
    )
    return result[0] if result else None


def _to_item(row: CotDerived, with_explanation: bool = False) -> CurrencyBiasItem:
    expl = None
    if with_explanation:
        expl = currency_explanation(
            symbol=row.currency,
            bias_label=row.bias_label,
            dir_score=row.dir_score,
            mom_score=row.mom_score,
            percentile=row.percentile,
            reversal_risk=row.reversal_risk,
            commercial_opposition=row.commercial_opposition,
            extreme_score=row.extreme_score,
        )
    return CurrencyBiasItem(
        currency=row.currency,
        bias_label=row.bias_label,
        currency_score=row.currency_score,
        dir_score=row.dir_score,
        mom_score=row.mom_score,
        strength_score=row.strength_score,
        percentile=row.percentile,
        extreme_score=row.extreme_score,
        reversal_risk=row.reversal_risk,
        reversal_score=row.reversal_score,
        commercial_opposition=row.commercial_opposition,
        nc_net=row.nc_net,
        net_change=row.net_change,
        net_pct_oi=row.net_pct_oi,
        explanation=expl,
    )


@router.get("", response_model=CurrenciesResponse)
def get_currencies(
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rd = date.fromisoformat(report_date) if report_date else _latest_date(db)
    if not rd:
        return CurrenciesResponse()

    rows = (
        db.query(CotDerived)
        .filter(CotDerived.report_date == rd, CotDerived.currency_score.isnot(None))
        .order_by(CotDerived.currency_score.desc())
        .all()
    )
    return CurrenciesResponse(
        report_date=rd,
        publish_date=rd + timedelta(days=3),
        currencies=[_to_item(r, with_explanation=True) for r in rows],
    )


@router.get("/{symbol}", response_model=CurrencyDetailResponse)
def get_currency_detail(
    symbol: str,
    report_date: Optional[str] = Query(None),
    history_weeks: int = Query(52, ge=4, le=260),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()
    rd = date.fromisoformat(report_date) if report_date else _latest_date(db)
    if not rd:
        raise HTTPException(status_code=404, detail="No data available")

    current_row = (
        db.query(CotDerived)
        .filter(CotDerived.report_date == rd, CotDerived.currency == symbol)
        .first()
    )
    if not current_row:
        raise HTTPException(status_code=404, detail=f"No data for {symbol} at {rd}")

    hist_rows = (
        db.query(CotDerived)
        .filter(CotDerived.currency == symbol, CotDerived.report_date <= rd)
        .order_by(CotDerived.report_date.desc())
        .limit(history_weeks)
        .all()
    )
    history = [
        CurrencyHistoryPoint(
            report_date=r.report_date,
            nc_net=r.nc_net,
            comm_net=r.comm_net,
            net_change=r.net_change,
            net_pct_oi=r.net_pct_oi,
            percentile=r.percentile,
            currency_score=r.currency_score,
            bias_label=r.bias_label,
            extreme_score=r.extreme_score,
            reversal_risk=r.reversal_risk,
        )
        for r in reversed(hist_rows)
    ]

    return CurrencyDetailResponse(
        currency=symbol,
        report_date=rd,
        current=_to_item(current_row, with_explanation=True),
        history=history,
        available_dates=_available_dates(db),
    )
