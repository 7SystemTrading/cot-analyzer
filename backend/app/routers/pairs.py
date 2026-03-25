"""
GET /api/v1/pairs         – all 28 pairs for a week
GET /api/v1/pairs/{pair}  – single pair with history + divergence
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CotDerived, CotPairs
from app.schemas import (
    PairBiasItem,
    PairDetailResponse,
    PairHistoryPoint,
    PairsResponse,
)
from app.services.commentary import currency_explanation, pair_explanation

router = APIRouter(prefix="/api/v1/pairs", tags=["pairs"])


def _latest_date(db: Session) -> Optional[date]:
    result = (
        db.query(CotPairs.report_date)
        .filter(CotPairs.pair_score.isnot(None))
        .order_by(CotPairs.report_date.desc())
        .first()
    )
    return result[0] if result else None


def _available_dates(db: Session) -> list[date]:
    rows = (
        db.query(CotPairs.report_date)
        .filter(CotPairs.pair_score.isnot(None))
        .distinct()
        .order_by(CotPairs.report_date.desc())
        .all()
    )
    return [r[0] for r in rows]


def _rr_for(db: Session, currency: str, rd: date) -> Optional[str]:
    row = (
        db.query(CotDerived.reversal_risk)
        .filter(CotDerived.currency == currency, CotDerived.report_date == rd)
        .first()
    )
    return row[0] if row else None


def _to_pair_item(p: CotPairs, db: Session, rd: date, with_explanation: bool = False) -> PairBiasItem:
    base_rr  = _rr_for(db, p.base_currency, rd)
    quote_rr = _rr_for(db, p.quote_currency, rd)
    expl = None
    if with_explanation:
        base_row = db.query(CotDerived).filter(
            CotDerived.currency == p.base_currency, CotDerived.report_date == rd
        ).first()
        quote_row = db.query(CotDerived).filter(
            CotDerived.currency == p.quote_currency, CotDerived.report_date == rd
        ).first()
        if base_row and quote_row:
            expl = pair_explanation(
                pair=p.pair, pair_label=p.pair_label,
                base=p.base_currency, quote=p.quote_currency,
                base_bias=base_row.bias_label or "Neutral",
                quote_bias=quote_row.bias_label or "Neutral",
                conviction=p.conviction or "Low",
                base_reversal=base_rr, quote_reversal=quote_rr,
                divergence_type=p.divergence_type,
                divergence_strength=p.divergence_strength,
            )
    return PairBiasItem(
        pair=p.pair,
        base_currency=p.base_currency,
        quote_currency=p.quote_currency,
        pair_score=p.pair_score,
        pair_label=p.pair_label,
        base_score=p.base_score,
        quote_score=p.quote_score,
        conviction=p.conviction,
        conviction_score=p.conviction_score,
        base_reversal_risk=base_rr,
        quote_reversal_risk=quote_rr,
        divergence_type=p.divergence_type,
        divergence_strength=p.divergence_strength,
        explanation=expl,
    )


@router.get("", response_model=PairsResponse)
def get_pairs(
    report_date: Optional[str] = Query(None),
    label_filter: Optional[str] = Query(None, description="Filter by pair_label (partial match)"),
    conviction_filter: Optional[str] = Query(None, description="High/Medium/Low"),
    divergence_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    rd = date.fromisoformat(report_date) if report_date else _latest_date(db)
    if not rd:
        return PairsResponse()

    query = db.query(CotPairs).filter(
        CotPairs.report_date == rd, CotPairs.pair_score.isnot(None)
    )
    if conviction_filter:
        query = query.filter(CotPairs.conviction == conviction_filter)
    if divergence_only:
        query = query.filter(CotPairs.divergence_type.isnot(None))

    rows = query.order_by(CotPairs.pair_score.desc()).all()

    if label_filter:
        rows = [r for r in rows if label_filter.lower() in (r.pair_label or "").lower()]

    pairs = [_to_pair_item(p, db, rd) for p in rows]
    return PairsResponse(
        report_date=rd,
        publish_date=rd + timedelta(days=3),
        pairs=pairs,
        available_dates=_available_dates(db),
    )


@router.get("/{pair_name}", response_model=PairDetailResponse)
def get_pair_detail(
    pair_name: str,
    report_date: Optional[str] = Query(None),
    history_weeks: int = Query(52, ge=4, le=260),
    db: Session = Depends(get_db),
):
    pair_name = pair_name.upper()
    rd = date.fromisoformat(report_date) if report_date else _latest_date(db)
    if not rd:
        raise HTTPException(status_code=404, detail="No data available")

    current = (
        db.query(CotPairs)
        .filter(CotPairs.pair == pair_name, CotPairs.report_date == rd)
        .first()
    )
    if not current:
        raise HTTPException(status_code=404, detail=f"No data for {pair_name} at {rd}")

    base  = pair_name[:3]
    quote = pair_name[3:]

    base_row = db.query(CotDerived).filter(
        CotDerived.currency == base, CotDerived.report_date == rd
    ).first()
    quote_row = db.query(CotDerived).filter(
        CotDerived.currency == quote, CotDerived.report_date == rd
    ).first()

    def _ccy_item(row):
        if not row:
            return None
        expl = currency_explanation(
            symbol=row.currency, bias_label=row.bias_label,
            dir_score=row.dir_score, mom_score=row.mom_score,
            percentile=row.percentile, reversal_risk=row.reversal_risk,
            commercial_opposition=row.commercial_opposition,
            extreme_score=row.extreme_score,
        )
        from app.schemas import CurrencyBiasItem
        return CurrencyBiasItem(
            currency=row.currency, bias_label=row.bias_label,
            currency_score=row.currency_score, dir_score=row.dir_score,
            mom_score=row.mom_score, strength_score=row.strength_score,
            percentile=row.percentile, extreme_score=row.extreme_score,
            reversal_risk=row.reversal_risk, reversal_score=row.reversal_score,
            commercial_opposition=row.commercial_opposition,
            nc_net=row.nc_net, net_change=row.net_change,
            net_pct_oi=row.net_pct_oi, explanation=expl,
        )

    hist_rows = (
        db.query(CotPairs)
        .filter(CotPairs.pair == pair_name, CotPairs.report_date <= rd)
        .order_by(CotPairs.report_date.desc())
        .limit(history_weeks)
        .all()
    )

    # Build nc_net lookup for base and quote currencies over the same date range
    hist_dates = [r.report_date for r in hist_rows]
    derived_rows = (
        db.query(CotDerived)
        .filter(
            CotDerived.currency.in_([base, quote]),
            CotDerived.report_date.in_(hist_dates),
        )
        .all()
    )
    nc_net_map: dict[tuple, float] = {
        (r.currency, r.report_date): r.nc_net for r in derived_rows
    }

    history = [
        PairHistoryPoint(
            report_date=r.report_date,
            pair_score=r.pair_score,
            pair_label=r.pair_label,
            conviction=r.conviction,
            divergence_type=r.divergence_type,
            base_nc_net=nc_net_map.get((base, r.report_date)),
            quote_nc_net=nc_net_map.get((quote, r.report_date)),
        )
        for r in reversed(hist_rows)
    ]

    return PairDetailResponse(
        pair=pair_name,
        report_date=rd,
        current=_to_pair_item(current, db, rd, with_explanation=True),
        base_detail=_ccy_item(base_row),
        quote_detail=_ccy_item(quote_row),
        history=history,
        available_dates=_available_dates(db),
    )
