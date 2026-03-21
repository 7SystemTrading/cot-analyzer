from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PairMetrics
from app.schemas import PairMetricsOut

router = APIRouter(prefix="/api/v1/pairs", tags=["pairs"])


@router.get("/ranking", response_model=List[PairMetricsOut])
def get_pair_ranking(
    report_date: Optional[str] = Query(None, description="YYYY-MM-DD, oletuksena uusin"),
    min_abs_score: float = Query(0.0, description="Suodatin: näytä vain parit, joissa |score| >= arvo"),
    db: Session = Depends(get_db),
):
    """Palauttaa kaikkien valuuttaparien rankingin yhdeltä viikolta."""
    if report_date:
        from datetime import date
        try:
            rd = date.fromisoformat(report_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Virheellinen päivämäärä")
    else:
        latest = (
            db.query(PairMetrics.report_date)
            .filter(PairMetrics.pair_score.isnot(None))
            .order_by(PairMetrics.report_date.desc())
            .first()
        )
        if not latest:
            return []
        rd = latest[0]

    rows = (
        db.query(PairMetrics)
        .filter(PairMetrics.report_date == rd)
        .filter(PairMetrics.pair_score.isnot(None))
        .order_by(PairMetrics.pair_score.desc())
        .all()
    )

    result = [PairMetricsOut.model_validate(r) for r in rows]
    if min_abs_score > 0:
        result = [p for p in result if abs(p.pair_score or 0) >= min_abs_score]

    return result


@router.get("/{pair}/history", response_model=List[PairMetricsOut])
def get_pair_history(
    pair: str,
    weeks: int = Query(52, ge=1, le=260),
    db: Session = Depends(get_db),
):
    """Palauttaa yksittäisen valuuttaparin historian viimeisiltä N viikolta."""
    pair = pair.upper()
    rows = (
        db.query(PairMetrics)
        .filter(PairMetrics.pair == pair)
        .filter(PairMetrics.pair_score.isnot(None))
        .order_by(PairMetrics.report_date.desc())
        .limit(weeks)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Ei dataa parille {pair}")
    return [PairMetricsOut.model_validate(r) for r in reversed(rows)]


@router.get("/heatmap", response_model=List[PairMetricsOut])
def get_heatmap_data(
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Palauttaa heatmap-datan (kaikki parit yhdeltä viikolta)."""
    return get_pair_ranking(report_date=report_date, min_abs_score=0.0, db=db)
