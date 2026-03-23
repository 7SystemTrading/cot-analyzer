from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CurrencyMetrics, PairMetrics, RawReport
from app.schemas import CurrencyMetricsOut, DashboardResponse, DataStatus, PairMetricsOut

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _get_data_status(db: Session) -> DataStatus:
    latest_raw = (
        db.query(RawReport.report_date, RawReport.publish_date)
        .filter(RawReport.is_corrected == False)  # noqa: E712
        .order_by(RawReport.report_date.desc())
        .first()
    )
    if not latest_raw:
        return DataStatus(status="no_data", message="Dataa ei ole ladattu. Aloita tuomalla COT-historia.")

    latest_date: date = latest_raw[0]
    latest_publish: date = latest_raw[1]
    total_weeks = (
        db.query(RawReport.report_date)
        .filter(RawReport.is_corrected == False)  # noqa: E712
        .distinct()
        .count()
    )

    # Tarkista viive: CFTC julkaisee tiistain datan perjantaina.
    days_old = (date.today() - latest_date).days
    if days_old > 14:
        status = "delayed"
        message = f"Uusin data mitattu {latest_date.isoformat()} ({days_old} päivää sitten)."
    else:
        status = "ok"
        message = f"Data ajantasalla."

    return DataStatus(
        latest_report_date=latest_date,
        latest_publish_date=latest_publish,
        total_weeks=total_weeks,
        status=status,
        message=message,
    )


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    report_date: Optional[str] = Query(None, description="YYYY-MM-DD, oletuksena uusin"),
    db: Session = Depends(get_db),
):
    data_status = _get_data_status(db)

    if data_status.status == "no_data":
        return DashboardResponse(data_status=data_status)

    if report_date:
        try:
            latest_date = date.fromisoformat(report_date)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Virheellinen päivämäärä")
    else:
        latest_cm = (
            db.query(CurrencyMetrics.report_date)
            .order_by(CurrencyMetrics.report_date.desc())
            .first()
        )
        if not latest_cm:
            return DashboardResponse(data_status=data_status)
        latest_date = latest_cm[0]

    currencies = (
        db.query(CurrencyMetrics)
        .filter(CurrencyMetrics.report_date == latest_date)
        .filter(CurrencyMetrics.currency_score.isnot(None))
        .order_by(CurrencyMetrics.currency_score.desc())
        .all()
    )

    pairs = (
        db.query(PairMetrics)
        .filter(PairMetrics.report_date == latest_date)
        .filter(PairMetrics.pair_score.isnot(None))
        .order_by(PairMetrics.pair_score.desc())
        .all()
    )

    return DashboardResponse(
        data_status=data_status,
        top_currencies=[CurrencyMetricsOut.model_validate(c) for c in currencies[:3]],
        bottom_currencies=[CurrencyMetricsOut.model_validate(c) for c in currencies[-3:][::-1]],
        top_pairs=[PairMetricsOut.model_validate(p) for p in pairs[:5]],
        bottom_pairs=[PairMetricsOut.model_validate(p) for p in pairs[-5:][::-1]],
    )
