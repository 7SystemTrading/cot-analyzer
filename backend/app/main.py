"""
COT Dashboard v2 – FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import SessionLocal, init_db
from app.models import CotRaw
from app.routers import currencies, import_data, overview, pairs
from app.routers import config_router
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _bootstrap_if_empty() -> None:
    """Auto-fetch 3 years of CFTC history on cold start if DB is empty."""
    db = SessionLocal()
    try:
        if db.query(CotRaw).count() > 0:
            logger.info("DB not empty – skipping bootstrap")
            return

        logger.info("DB empty – bootstrapping 3 years of COT history...")
        from app.services.cot_fetcher import fetch_year
        from app.services.importer import save_raw_data
        from app.services.calculator import recalculate_all

        current_year = date.today().year
        for year in range(current_year - 2, current_year + 1):
            try:
                df = await fetch_year(year)
                if not df.empty:
                    save_raw_data(db, df, source_type="auto", source_file=f"bootstrap_{year}")
                    logger.info("Bootstrap %d: %d rows", year, len(df))
            except Exception as e:
                logger.error("Bootstrap %d failed: %s", year, e)

        recalculate_all(db)
        logger.info("Bootstrap complete")
    except Exception as e:
        logger.error("Bootstrap error: %s", e)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database...")
    init_db()
    await _bootstrap_if_empty()
    logger.info("Starting scheduler...")
    start_scheduler()
    yield
    logger.info("Stopping scheduler...")
    stop_scheduler()


app = FastAPI(
    title="COT Dashboard v2",
    description="CFTC Legacy COT data → currency bias + divergence engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(currencies.router)
app.include_router(pairs.router)
app.include_router(import_data.router)
app.include_router(config_router.router)

# Serve React build
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info("Serving static files from: %s", static_dir)
else:
    @app.get("/")
    def root():
        return {"message": "COT Dashboard v2 API", "docs": "/docs", "version": "2.0.0"}
