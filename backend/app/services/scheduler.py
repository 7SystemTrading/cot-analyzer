"""
APScheduler – weekly COT data auto-fetch.
Runs every Friday at 22:00 UTC (CFTC publishes Friday afternoon US time).
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.services.calculator import recalculate_all
from app.services.cot_fetcher import fetch_latest
from app.services.importer import save_raw_data

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


async def _weekly_fetch() -> None:
    logger.info("Scheduled COT fetch starting...")
    db = SessionLocal()
    try:
        df = await fetch_latest()
        if df.empty:
            logger.warning("Scheduled fetch returned no data")
            return
        save_raw_data(db, df, source_type="auto", source_file="scheduled")
        recalculate_all(db)
        logger.info("Scheduled fetch complete")
    except Exception as e:
        logger.error("Scheduled fetch failed: %s", e)
    finally:
        db.close()


def start_scheduler() -> None:
    _scheduler.add_job(
        _weekly_fetch,
        trigger=CronTrigger(day_of_week="fri", hour=22, minute=0),
        id="weekly_cot_fetch",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started (weekly COT fetch: Friday 22:00 UTC)")


def stop_scheduler() -> None:
    _scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
