"""
POST /api/v1/data/fetch   – fetch CFTC data (year or all recent)
GET  /api/v1/data/status  – data status, latest week, import logs
"""
import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CotRaw, ImportLog
from app.schemas import DataStatusResponse, ImportLogItem
from app.services.calculator import recalculate_all
from app.services.cot_fetcher import fetch_latest, fetch_year
from app.services.importer import save_raw_data

router = APIRouter(prefix="/api/v1/data", tags=["data"])
logger = logging.getLogger(__name__)


async def _do_fetch_and_recalc(year: int | None, db: Session) -> None:
    try:
        if year:
            df = await fetch_year(year)
        else:
            df = await fetch_latest()

        if df.empty:
            logger.warning("Fetch returned no data")
            return

        save_raw_data(db, df, source_type="auto", source_file=f"fetch_{year or 'latest'}")
        recalculate_all(db)
        logger.info("Fetch and recalculation complete")
    except Exception as e:
        logger.error("Fetch failed: %s", e)


@router.post("/fetch")
async def fetch_data(
    year: int | None = Query(None, description="Specific year, or omit for latest"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Trigger a CFTC data fetch. Runs in background."""
    background_tasks.add_task(_do_fetch_and_recalc, year, db)
    return {"status": "started", "year": year or "latest"}


@router.get("/status", response_model=DataStatusResponse)
def get_data_status(
    db: Session = Depends(get_db),
):
    latest = (
        db.query(CotRaw.report_date)
        .order_by(CotRaw.report_date.desc())
        .first()
    )
    total_rows  = db.query(CotRaw).count()
    total_weeks = db.query(CotRaw.report_date).distinct().count()
    currencies  = [r[0] for r in db.query(CotRaw.currency).distinct().order_by(CotRaw.currency).all()]

    logs = (
        db.query(ImportLog)
        .order_by(ImportLog.imported_at.desc())
        .limit(10)
        .all()
    )

    return DataStatusResponse(
        latest_report_date=latest[0] if latest else None,
        total_weeks=total_weeks,
        total_rows=total_rows,
        currencies_covered=currencies,
        recent_logs=[
            ImportLogItem(
                id=lg.id,
                imported_at=str(lg.imported_at),
                source_type=lg.source_type,
                source_file=lg.source_file,
                rows_total=lg.rows_total or 0,
                rows_inserted=lg.rows_inserted or 0,
                rows_skipped=lg.rows_skipped or 0,
                status=lg.status or "ok",
                errors=lg.errors,
            )
            for lg in logs
        ],
    )
