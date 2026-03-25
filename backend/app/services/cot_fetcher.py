"""
COT Dashboard v2 – CFTC Legacy COT data fetcher.

Source: deahistfo{year}.zip  (Futures Only, Legacy COT format)
Contains: Non-commercial / Commercial / Non-reportable / Open Interest
"""
import io
import logging
import zipfile
from datetime import date
from typing import Optional

import httpx
import pandas as pd

from app.config import CFTC_BASE_URL, COT_COLUMNS, CURRENCY_CONTRACTS

logger = logging.getLogger(__name__)

_TIMEOUT = 60  # seconds


def _find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return the first matching column name (case-insensitive)."""
    lower_cols = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower_cols:
            return lower_cols[candidate.lower()]
    return None


def _parse_zip(content: bytes) -> pd.DataFrame:
    """Extract and parse the Legacy COT file from ZIP.

    Legacy COT ZIPs contain a plain-text CSV (e.g. annualof.txt).
    """
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = zf.namelist()
        # Prefer XLS/CSV; fall back to any .txt (Legacy COT uses annualof.txt)
        target = next(
            (n for n in names if n.lower().endswith((".xls", ".xlsx", ".csv"))),
            None,
        ) or next(
            (n for n in names if n.lower().endswith(".txt")),
            None,
        )
        if not target:
            raise ValueError(f"No data file found in ZIP. Contents: {names}")
        raw = zf.read(target)

    if target.lower().endswith((".xls", ".xlsx")):
        df = pd.read_excel(io.BytesIO(raw), engine="xlrd")
    else:
        # Legacy COT .txt files are comma-separated
        df = pd.read_csv(io.BytesIO(raw), low_memory=False)

    logger.debug("Parsed %d rows, %d columns from %s", len(df), len(df.columns), target)
    return df


def _extract_currencies(df: pd.DataFrame) -> pd.DataFrame:
    """Filter rows for the 8 forex currencies and rename to standard keys."""
    col_map = {}
    for key, canonical in COT_COLUMNS.items():
        found = _find_column(df, [canonical])
        if found:
            col_map[key] = found
        else:
            logger.warning("Column not found: %s", canonical)

    required = ["market", "date", "open_interest", "nc_long", "nc_short",
                "comm_long", "comm_short", "nr_long", "nr_short"]
    missing = [k for k in required if k not in col_map]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Available: {list(df.columns[:20])}"
        )

    date_col   = col_map["date"]
    market_col = col_map["market"]

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])

    rows = []
    for currency, prefix in CURRENCY_CONTRACTS.items():
        mask   = df[market_col].astype(str).str.startswith(prefix)
        subset = df[mask].copy()

        if subset.empty:
            logger.warning("No rows for %s (prefix: %s)", currency, prefix)
            continue

        for _, row in subset.iterrows():
            try:
                rows.append({
                    "report_date":   row[date_col].date(),
                    "currency":      currency,
                    "contract_name": str(row[market_col]),
                    "nc_long":       float(row[col_map["nc_long"]]),
                    "nc_short":      float(row[col_map["nc_short"]]),
                    "comm_long":     float(row[col_map["comm_long"]]),
                    "comm_short":    float(row[col_map["comm_short"]]),
                    "nr_long":       float(row[col_map["nr_long"]]),
                    "nr_short":      float(row[col_map["nr_short"]]),
                    "open_interest": float(row[col_map["open_interest"]]),
                })
            except (KeyError, ValueError) as e:
                logger.debug("Skipping row for %s: %s", currency, e)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).sort_values("report_date").reset_index(drop=True)
    logger.info(
        "Extracted %d rows for %d currencies",
        len(result), result["currency"].nunique()
    )
    return result


async def fetch_year(year: int) -> pd.DataFrame:
    """Download and parse one year of Legacy COT data."""
    url = CFTC_BASE_URL.format(year=year)
    logger.info("Fetching COT %d from %s", year, url)

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    df = _parse_zip(resp.content)
    return _extract_currencies(df)


async def fetch_latest() -> pd.DataFrame:
    """Fetch current year; also fetch previous year if data is thin."""
    today = date.today()
    df = await fetch_year(today.year)

    if df.empty or df["report_date"].max() < date(today.year, 1, 15):
        prev = await fetch_year(today.year - 1)
        df = pd.concat([prev, df], ignore_index=True)

    return df
