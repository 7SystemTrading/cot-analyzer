import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import ImportLog
from app.schemas import ImportLogOut, ImportResult

router = APIRouter(prefix="/api/v1/import", tags=["import"])
logger = logging.getLogger(__name__)


async def _bg_recalculate(session_factory):
    """Taustatyö: laskee kaiken uudelleen importin jälkeen."""
    from app.services.calculator import recalculate_all
    db = session_factory()
    try:
        recalculate_all(db)
    except Exception as e:
        logger.error("Taustatyö recalculate_all epäonnistui: %s", e)
    finally:
        db.close()


@router.post("/upload", response_model=ImportResult)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Lataa CSV tai Excel -tiedoston ja tuo datan tietokantaan."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Tiedostonimi puuttuu.")

    allowed_ext = (".csv", ".xlsx", ".xls")
    if not any(file.filename.lower().endswith(ext) for ext in allowed_ext):
        raise HTTPException(
            status_code=400,
            detail=f"Tuetut tiedostomuodot: {', '.join(allowed_ext)}",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Tiedosto on tyhjä.")

    from app.services.cot_fetcher import parse_uploaded_file
    from app.services.importer import save_raw_data

    try:
        df = parse_uploaded_file(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if df.empty:
        raise HTTPException(
            status_code=422,
            detail="Tiedostosta ei löytynyt tunnistettavaa COT-dataa.",
        )

    log = save_raw_data(db, df, source_type="manual", source_file=file.filename)

    if log.rows_inserted > 0:
        background_tasks.add_task(_bg_recalculate, SessionLocal)

    errors = log.errors.split("\n") if log.errors else []
    return ImportResult(
        status=log.status,
        rows_total=log.rows_total,
        rows_inserted=log.rows_inserted,
        rows_skipped=log.rows_skipped,
        errors=errors,
        message=(
            f"Tuonti onnistui: {log.rows_inserted} uutta riviä tallennettu, "
            f"{log.rows_skipped} ohitettu (duplikaatit)."
            if log.status != "failed"
            else f"Tuonti epäonnistui: {', '.join(errors)}"
        ),
    )


@router.post("/fetch-history", response_model=ImportResult)
async def fetch_history(
    background_tasks: BackgroundTasks,
    year: Optional[int] = Query(None, description="Yksittäinen vuosi. Jätä tyhjäksi kaikelle historialle (2010–nyt)."),
    db: Session = Depends(get_db),
):
    """Hakee historiallisen COT-datan CFTC:ltä (vuosittaiset ZIP-tiedostot)."""
    from app.services.cot_fetcher import fetch_history_all, fetch_year
    from app.services.importer import save_raw_data

    try:
        if year:
            df = await fetch_year(year)
            source_file = f"cftc_history_{year}"
        else:
            df = await fetch_history_all()
            source_file = "cftc_history_all"
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CFTC-haku epäonnistui: {e}")

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"CFTC:ltä ei saatu dataa {'vuodelle ' + str(year) if year else '(kaikki vuodet)'}.",
        )

    log = save_raw_data(db, df, source_type="history", source_file=source_file)

    if log.rows_inserted > 0:
        background_tasks.add_task(_bg_recalculate, SessionLocal)

    errors = log.errors.split("\n") if log.errors else []
    return ImportResult(
        status=log.status,
        rows_total=log.rows_total,
        rows_inserted=log.rows_inserted,
        rows_skipped=log.rows_skipped,
        errors=errors,
        message=(
            f"Historia haettu: {log.rows_inserted} uutta riviä tallennettu."
            if log.status != "failed"
            else f"Haku epäonnistui: {', '.join(errors)}"
        ),
    )


@router.post("/fetch-latest", response_model=ImportResult)
async def fetch_latest(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Hakee viimeisimmän viikon COT-datan CFTC:n API:sta."""
    from app.services.cot_fetcher import fetch_current_week
    from app.services.importer import save_raw_data

    try:
        df = await fetch_current_week()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CFTC-haku epäonnistui: {e}")

    if df.empty:
        raise HTTPException(status_code=404, detail="CFTC:ltä ei saatu dataa.")

    log = save_raw_data(db, df, source_type="auto", source_file="cftc_weekly")

    if log.rows_inserted > 0:
        background_tasks.add_task(_bg_recalculate, SessionLocal)

    errors = log.errors.split("\n") if log.errors else []
    return ImportResult(
        status=log.status,
        rows_total=log.rows_total,
        rows_inserted=log.rows_inserted,
        rows_skipped=log.rows_skipped,
        errors=errors,
        message=(
            f"Uusin viikko haettu: {log.rows_inserted} uutta riviä tallennettu."
            if log.status != "failed"
            else f"Haku epäonnistui: {', '.join(errors)}"
        ),
    )


@router.get("/logs", response_model=List[ImportLogOut])
def get_import_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Palauttaa viimeisimmät import-lokit."""
    rows = (
        db.query(ImportLog)
        .order_by(ImportLog.imported_at.desc())
        .limit(limit)
        .all()
    )
    return [ImportLogOut.model_validate(r) for r in rows]
