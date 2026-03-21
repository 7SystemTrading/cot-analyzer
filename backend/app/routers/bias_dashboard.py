"""
COT Bias Dashboard API – erillinen laskentamalli.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import BiasDashboardResponse
from app.services.bias_calculator import DEFAULT_THRESHOLD, compute_bias_dashboard

router = APIRouter(prefix="/api/v1/bias-dashboard", tags=["bias-dashboard"])


@router.get("", response_model=BiasDashboardResponse)
def get_bias_dashboard(
    report_date: Optional[str] = Query(None, description="YYYY-MM-DD, oletuksena uusin"),
    threshold: float = Query(DEFAULT_THRESHOLD, ge=1, le=50, description="Kynnysarvo (oletus 25)"),
    db: Session = Depends(get_db),
):
    """
    Palauttaa COT Bias Dashboard -datan: Strong Long, Strong Short ja valuuttayhteenveto.
    """
    rd = None
    if report_date:
        try:
            rd = date.fromisoformat(report_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Virheellinen päivämäärä, käytä YYYY-MM-DD")

    result = compute_bias_dashboard(db, report_date=rd, threshold=threshold)
    return BiasDashboardResponse(**result)
