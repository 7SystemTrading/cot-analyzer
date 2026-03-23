"""
Tietokannan kirjoitusoperaatiot COT-datalle.
Huolehtii validoinnista, duplikaattien ohituksesta ja audit trailista.
"""
import logging
from datetime import date, timedelta
from typing import List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import ImportLog, RawReport
from app.services import calculator

logger = logging.getLogger(__name__)


def _validate_df(df: pd.DataFrame) -> list[str]:
    """Palauttaa listan validointivirheistä. Tyhjä lista = OK."""
    errors = []
    if df.empty:
        errors.append("Tiedosto ei sisällä käyttökelpoista dataa.")
        return errors

    required = ["report_date", "currency", "open_interest_total", "lev_long", "lev_short"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        errors.append(f"Puuttuvat sarakkeet: {', '.join(missing)}")

    if "currency" in df.columns:
        unknown = set(df["currency"].unique()) - {
            "EUR", "GBP", "JPY", "CAD", "CHF", "AUD", "NZD", "USD"
        }
        if unknown:
            errors.append(f"Tuntemattomat valuutat: {', '.join(unknown)}")

    return errors


def save_raw_data(
    db: Session,
    df: pd.DataFrame,
    source_type: str = "manual",
    source_file: Optional[str] = None,
) -> ImportLog:
    """
    Tallentaa raakadatan tietokantaan.
    Skipaa duplikaatit (report_date + currency).
    Palauttaa ImportLog-objektin.
    """
    errors = _validate_df(df)
    if errors:
        log = ImportLog(
            source_type=source_type,
            source_file=source_file,
            rows_total=len(df),
            rows_inserted=0,
            rows_skipped=0,
            errors="\n".join(errors),
            status="failed",
        )
        db.add(log)
        db.commit()
        return log

    inserted = 0
    skipped = 0
    row_errors = []

    for _, row in df.iterrows():
        try:
            report_date = row["report_date"]
            if isinstance(report_date, str):
                report_date = date.fromisoformat(report_date)
            elif hasattr(report_date, "date"):
                report_date = report_date.date()

            # Tarkista duplikaatti
            exists = (
                db.query(RawReport)
                .filter(
                    RawReport.report_date == report_date,
                    RawReport.currency == row["currency"],
                    RawReport.is_corrected == False,  # noqa: E712
                )
                .first()
            )
            if exists:
                skipped += 1
                continue

            # Laske julkaisupäivä: report_date on tiistai, julkaisu on perjantai (+3 pv)
            publish_date = report_date + timedelta(days=3)

            record = RawReport(
                report_date=report_date,
                publish_date=publish_date,
                currency=str(row["currency"]),
                contract_name=row.get("contract_name"),
                open_interest_total=float(row["open_interest_total"]),
                lev_long=float(row["lev_long"]),
                lev_short=float(row["lev_short"]),
                lev_spreading=float(row.get("lev_spreading", 0.0)),
                source_file=source_file,
            )
            db.add(record)
            inserted += 1

        except Exception as e:
            row_errors.append(str(e))
            logger.warning("Rivin tallennus epäonnistui: %s", e)

    db.commit()

    status = "ok" if not row_errors else "partial"
    log = ImportLog(
        source_type=source_type,
        source_file=source_file,
        rows_total=len(df),
        rows_inserted=inserted,
        rows_skipped=skipped,
        errors="\n".join(row_errors) if row_errors else None,
        status=status,
    )
    db.add(log)
    db.commit()

    logger.info(
        "Import valmis: %d tallennettu, %d skipattu, %d virhettä",
        inserted,
        skipped,
        len(row_errors),
    )
    return log


def get_new_dates_after_import(db: Session, log: ImportLog) -> List[date]:
    """
    Palauttaa raporttipäivät, joille pitää ajaa laskenta.
    Käytetään triggerin yhteydessä.
    """
    if log.status == "failed" or log.rows_inserted == 0:
        return []

    # Hae kaikki raporttiviikot, joille ei vielä ole CurrencyMetrics
    from app.models import CurrencyMetrics

    existing_dates = {
        r.report_date
        for r in db.query(CurrencyMetrics.report_date).distinct().all()
    }
    all_raw_dates = {
        r.report_date
        for r in db.query(RawReport.report_date).distinct().all()
    }
    return sorted(all_raw_dates - existing_dates)


def run_full_recalculation(db: Session) -> int:
    """Laskee kaiken uudelleen raakadatasta. Palauttaa käsiteltyjen viikkojen määrän."""
    from app.services.calculator import recalculate_all

    return recalculate_all(db)
