"""
APScheduler – viikoittainen COT-datan haku.
Käynnistyy FastAPI:n lifespan-hookissa.
"""
import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _fetch_and_save_latest():
    """Hakee uusimman viikon datan ja tallentaa sen."""
    from app.services.cot_fetcher import fetch_current_week
    from app.services.importer import save_raw_data
    from app.services.calculator import recalculate_all

    logger.info("Ajastettu haku: haetaan uusin COT-data...")
    db: Session = SessionLocal()
    try:
        df = await fetch_current_week()
        if df.empty:
            logger.warning("Ajastettu haku: ei dataa saatavilla.")
            return

        log = save_raw_data(db, df, source_type="auto", source_file="cftc_weekly_auto")
        if log.rows_inserted > 0:
            logger.info("Ajastettu haku: %d uutta riviä tallennettu, lasketaan uudelleen...", log.rows_inserted)
            recalculate_all(db)
        else:
            logger.info("Ajastettu haku: ei uusia rivejä (jo ajantasalla).")
    except Exception as e:
        logger.error("Ajastettu haku epäonnistui: %s", e)
    finally:
        db.close()


def start_scheduler():
    """Rekisteröi ja käynnistää schedulerin."""
    # Perjantaisin klo 22:00 UTC (CFTC julkaisee ~15:30 ET = ~20:30 UTC)
    scheduler.add_job(
        _fetch_and_save_latest,
        trigger=CronTrigger(day_of_week="fri", hour=22, minute=0),
        id="weekly_cot_fetch",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler käynnistetty – COT-haku perjantaisin klo 22:00 UTC")


def stop_scheduler():
    """Pysäyttää schedulerin."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler pysäytetty.")
