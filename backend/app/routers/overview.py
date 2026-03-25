"""
GET /api/v1/overview
Returns currency ranking, top pairs, extremes, available dates.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CotDerived, CotPairs, CotRaw
from app.schemas import CurrencyBiasItem, EventItem, ExtremeItem, OverviewResponse, PairBiasItem
from app.services.commentary import currency_explanation, pair_explanation

router = APIRouter(prefix="/api/v1/overview", tags=["overview"])


def _latest_date(db: Session) -> Optional[date]:
    result = (
        db.query(CotDerived.report_date)
        .filter(CotDerived.currency_score.isnot(None))
        .order_by(CotDerived.report_date.desc())
        .first()
    )
    return result[0] if result else None


def _build_currency_item(row: CotDerived, include_explanation: bool = False) -> CurrencyBiasItem:
    expl = None
    if include_explanation:
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


@router.get("", response_model=OverviewResponse)
def get_overview(
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rd = date.fromisoformat(report_date) if report_date else _latest_date(db)
    if not rd:
        return OverviewResponse()

    publish_date = rd + timedelta(days=3)

    # Currency ranking (sorted by score descending)
    ccy_rows = (
        db.query(CotDerived)
        .filter(CotDerived.report_date == rd, CotDerived.currency_score.isnot(None))
        .order_by(CotDerived.currency_score.desc())
        .all()
    )
    currencies_ranked = [_build_currency_item(r) for r in ccy_rows]

    # Build reversal risk lookup for pairs
    rr_map = {r.currency: r.reversal_risk for r in ccy_rows}
    bias_map = {r.currency: r.bias_label for r in ccy_rows}

    # Top pairs (highest |pair_score|, max 10)
    pair_rows = (
        db.query(CotPairs)
        .filter(CotPairs.report_date == rd, CotPairs.pair_score.isnot(None))
        .order_by(CotPairs.pair_score.desc())
        .all()
    )
    pair_rows_sorted = sorted(pair_rows, key=lambda p: abs(p.pair_score or 0), reverse=True)

    top_pairs = []
    for p in pair_rows_sorted[:10]:
        top_pairs.append(PairBiasItem(
            pair=p.pair,
            base_currency=p.base_currency,
            quote_currency=p.quote_currency,
            pair_score=p.pair_score,
            pair_label=p.pair_label,
            base_score=p.base_score,
            quote_score=p.quote_score,
            conviction=p.conviction,
            conviction_score=p.conviction_score,
            base_reversal_risk=rr_map.get(p.base_currency),
            quote_reversal_risk=rr_map.get(p.quote_currency),
            divergence_type=p.divergence_type,
            divergence_strength=p.divergence_strength,
        ))

    # Extremes (extreme_score >= 2)
    extremes = [
        ExtremeItem(
            currency=r.currency,
            bias_label=r.bias_label,
            extreme_score=r.extreme_score,
            percentile=r.percentile,
            reversal_risk=r.reversal_risk,
        )
        for r in ccy_rows
        if r.extreme_score is not None and r.extreme_score >= 2
    ]
    extremes.sort(key=lambda e: e.extreme_score or 0, reverse=True)

    # Event detection: compare current week vs previous week
    events: list[EventItem] = []
    prev_dates = (
        db.query(CotDerived.report_date)
        .filter(CotDerived.report_date < rd, CotDerived.currency_score.isnot(None))
        .order_by(CotDerived.report_date.desc())
        .limit(1)
        .all()
    )
    if prev_dates:
        prev_rd = prev_dates[0][0]
        prev_rows = (
            db.query(CotDerived)
            .filter(CotDerived.report_date == prev_rd)
            .all()
        )
        prev_map = {r.currency: r for r in prev_rows}
        for r in ccy_rows:
            prev = prev_map.get(r.currency)
            if not prev:
                continue
            # Bias shift
            if prev.bias_label and r.bias_label and prev.bias_label != r.bias_label:
                events.append(EventItem(
                    event_type="bias_shift",
                    subject=r.currency,
                    detail=f"{r.currency}: {prev.bias_label} → {r.bias_label}",
                ))
            # New extreme (extreme_score just crossed to >= 2)
            prev_extreme = prev.extreme_score or 0
            curr_extreme = r.extreme_score or 0
            if curr_extreme >= 2 and prev_extreme < 2:
                level = "Historical" if curr_extreme == 3 else "Major"
                events.append(EventItem(
                    event_type="new_extreme",
                    subject=r.currency,
                    detail=f"{r.currency} reached {level} extreme positioning",
                ))

        # New divergences on pairs
        prev_pair_rows = (
            db.query(CotPairs)
            .filter(CotPairs.report_date == prev_rd, CotPairs.divergence_type.isnot(None))
            .all()
        )
        prev_div_pairs = {r.pair for r in prev_pair_rows}
        curr_pair_rows = (
            db.query(CotPairs)
            .filter(CotPairs.report_date == rd, CotPairs.divergence_type.isnot(None))
            .all()
        )
        for p in curr_pair_rows:
            if p.pair not in prev_div_pairs:
                events.append(EventItem(
                    event_type="new_divergence",
                    subject=p.pair,
                    detail=f"{p.pair}: new {p.divergence_type} divergence detected",
                ))

    # Available dates
    dates = [
        r[0] for r in
        db.query(CotDerived.report_date)
        .filter(CotDerived.currency_score.isnot(None))
        .distinct()
        .order_by(CotDerived.report_date.desc())
        .limit(104)
        .all()
    ]

    return OverviewResponse(
        report_date=rd,
        publish_date=publish_date,
        currencies_ranked=currencies_ranked,
        top_pairs=top_pairs,
        extremes=extremes,
        events=events,
        available_dates=dates,
    )
