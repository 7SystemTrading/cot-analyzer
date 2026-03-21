import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import SessionLocal, init_db
from app.models import RawReport
from app.routers import bias_dashboard, config_router, currencies, dashboard, import_data, pairs
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _bootstrap_data_if_empty():
    """Hakee CFTC-historian automaattisesti jos tietokanta on tyhjä (Render redeploy)."""
    db = SessionLocal()
    try:
        count = db.query(RawReport).count()
        if count > 0:
            logger.info("Tietokannassa %d riviä – bootstrap ei tarpeen.", count)
            return

        logger.info("Tietokanta tyhjä – haetaan 3 vuoden CFTC-historia automaattisesti...")
        from app.services.cot_fetcher import fetch_year
        from app.services.importer import save_raw_data
        from app.services.calculator import recalculate_all

        current_year = date.today().year
        for year in range(current_year - 2, current_year + 1):
            try:
                df = await fetch_year(year)
                if not df.empty:
                    save_raw_data(db, df, source_type="auto", source_file=f"bootstrap_{year}")
                    logger.info("Bootstrap %d: %d riviä", year, len(df))
            except Exception as e:
                logger.error("Bootstrap %d epäonnistui: %s", year, e)

        recalculate_all(db)
        logger.info("Bootstrap valmis – data ladattu ja laskettu.")
    except Exception as e:
        logger.error("Bootstrap epäonnistui: %s", e)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Käynnistys
    logger.info("Alustetaan tietokanta...")
    init_db()
    await _bootstrap_data_if_empty()
    logger.info("Käynnistetään ajastin...")
    start_scheduler()
    yield
    # Sammutus
    logger.info("Pysäytetään ajastin...")
    stop_scheduler()


app = FastAPI(
    title="COT Currency Strength Bias Analyzer",
    description="Analysoi CFTC:n COT-dataa valuuttakohtaisten vahvuuspisteiden laskemiseksi.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – salli kehitysaikana kaikki, tuotannossa rajoita
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API-reititys
app.include_router(dashboard.router)
app.include_router(currencies.router)
app.include_router(pairs.router)
app.include_router(import_data.router)
app.include_router(config_router.router)
app.include_router(bias_dashboard.router)

# Staattisten tiedostojen palveleminen (React-build)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info("Staattiset tiedostot palvellaan hakemistosta: %s", static_dir)
else:
    logger.info(
        "Staattisia tiedostoja ei löydy (%s). Pelkkä API-tila.", static_dir
    )

    @app.get("/")
    def root():
        return {
            "message": "COT Currency Strength Bias Analyzer API",
            "docs": "/docs",
            "version": "1.0.0",
        }
