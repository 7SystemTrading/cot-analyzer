"""
GET /api/v1/config   – read current settings
PUT /api/v1/config   – update settings and trigger recalculation
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppSettings
from app.schemas import AppSettingsSchema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/config", tags=["config"])


def _get_or_create(db: Session) -> AppSettings:
    row = db.query(AppSettings).first()
    if not row:
        row = AppSettings()
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=AppSettingsSchema)
def get_config(db: Session = Depends(get_db)):
    row = _get_or_create(db)
    return AppSettingsSchema(
        percentile_window=row.percentile_window,
        divergence_window=row.divergence_window,
        weight_direction=row.weight_direction,
        weight_momentum=row.weight_momentum,
        weight_strength=row.weight_strength,
        extreme_threshold_mild=row.extreme_threshold_mild,
        extreme_threshold_major=row.extreme_threshold_major,
        extreme_threshold_historic=row.extreme_threshold_historic,
    )


@router.put("", response_model=AppSettingsSchema)
def update_config(
    body: AppSettingsSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    row = _get_or_create(db)
    row.percentile_window          = body.percentile_window
    row.divergence_window          = body.divergence_window
    row.weight_direction           = body.weight_direction
    row.weight_momentum            = body.weight_momentum
    row.weight_strength            = body.weight_strength
    row.extreme_threshold_mild     = body.extreme_threshold_mild
    row.extreme_threshold_major    = body.extreme_threshold_major
    row.extreme_threshold_historic = body.extreme_threshold_historic
    db.commit()
    db.refresh(row)

    # Trigger recalculation in background so new settings take effect
    def _recalc():
        from app.database import SessionLocal
        from app.services.calculator import recalculate_all
        session = SessionLocal()
        try:
            recalculate_all(session)
            logger.info("Recalculation triggered by config change")
        finally:
            session.close()

    background_tasks.add_task(_recalc)
    logger.info("Settings updated, recalculation queued")

    return AppSettingsSchema(
        percentile_window=row.percentile_window,
        divergence_window=row.divergence_window,
        weight_direction=row.weight_direction,
        weight_momentum=row.weight_momentum,
        weight_strength=row.weight_strength,
        extreme_threshold_mild=row.extreme_threshold_mild,
        extreme_threshold_major=row.extreme_threshold_major,
        extreme_threshold_historic=row.extreme_threshold_historic,
    )
