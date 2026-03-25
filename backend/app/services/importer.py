"""
COT Dashboard v2 – Database write operations.
Handles deduplication, import logging, and triggering recalculation.
"""
import logging
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.models import CotRaw, ImportLog

logger = logging.getLogger(__name__)


def save_raw_data(
    db: Session,
    df: pd.DataFrame,
    source_type: str = "manual",
    source_file: str = "",
) -> ImportLog:
    """
    Insert rows from df into cot_raw, skipping duplicates.
    Returns an ImportLog record.
    """
    total     = len(df)
    inserted  = 0
    skipped   = 0
    errors    = []

    for _, row in df.iterrows():
        try:
            rd  = row["report_date"]
            ccy = row["currency"]

            try:
                existing = (
                    db.query(CotRaw)
                    .filter(CotRaw.report_date == rd, CotRaw.currency == ccy)
                    .first()
                )
            except Exception:
                db.rollback()
                skipped += 1
                continue

            if existing:
                skipped += 1
                continue

            db.add(CotRaw(
                report_date   = rd,
                currency      = ccy,
                contract_name = row.get("contract_name"),
                nc_long       = float(row["nc_long"]),
                nc_short      = float(row["nc_short"]),
                comm_long     = float(row["comm_long"]),
                comm_short    = float(row["comm_short"]),
                nr_long       = float(row["nr_long"]),
                nr_short      = float(row["nr_short"]),
                open_interest = float(row["open_interest"]),
                source_file   = source_file,
            ))
            inserted += 1

        except Exception as e:
            db.rollback()
            errors.append(str(e))
            logger.warning("Error inserting row: %s", e)

    db.commit()

    status = "ok" if not errors else ("partial" if inserted > 0 else "failed")
    log = ImportLog(
        source_type   = source_type,
        source_file   = source_file,
        rows_total    = total,
        rows_inserted = inserted,
        rows_skipped  = skipped,
        errors        = "; ".join(errors[:10]) if errors else None,
        status        = status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    logger.info(
        "Import done: %d inserted, %d skipped, %d errors",
        inserted, skipped, len(errors)
    )
    return log
