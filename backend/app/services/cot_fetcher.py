"""
CFTC COT Financial Futures -datan haku.
Tukee sekä historiallista bulk-latausta (ZIP vuosittain) että
viimeisimmän viikon hakemista CFTC:n julkisesta API:sta.
"""
import io
import logging
import zipfile
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
import pandas as pd

from app.config import (
    CFTC_COLUMNS,
    CFTC_CURRENT_URL,
    CFTC_FIRST_YEAR,
    CFTC_HISTORY_URL_TEMPLATE,
    CURRENCIES,
    CURRENCY_CONTRACTS,
)

logger = logging.getLogger(__name__)

# Sopimustunnisteet: etsitään osittaisella nimellä (isoilla kirjaimilla)
_CONTRACT_SEARCH: dict[str, str] = {
    ccy: name.upper() for ccy, name in CURRENCY_CONTRACTS.items()
}


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Etsii ensimmäisen vastaavan sarakkeen. Case-insensitive."""
    df_cols_upper = {c.upper(): c for c in df.columns}
    for cand in candidates:
        if cand.upper() in df_cols_upper:
            return df_cols_upper[cand.upper()]
    return None


def _parse_raw_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Poimitaan CFTC:n raakadataframesta tarvittavat valuutat.
    Tukee useita sarakenimi-variantteja (Excel/CSV/API-muodot eroavat).
    """
    # Normalisoidaan sarakenimet (trim)
    df.columns = [c.strip() for c in df.columns]

    # Etsitään sarakkeet joustavasti – CFTC käyttää eri nimiä eri lähteissä
    date_col = _find_column(df, [
        "Report_Date_as_MM_DD_YYYY",
        "Report_Date_as_YYYY_MM_DD",
        "Report_Date_as_YYYY-MM-DD",
        "As_of_Date_In_Form_YYMMDD",
    ])
    market_col = _find_column(df, [
        "Market_and_Exchange_Names",
        "Contract_Market_Name",
    ])
    oi_col = _find_column(df, ["Open_Interest_All"])
    long_col = _find_column(df, ["Lev_Money_Positions_Long_All"])
    short_col = _find_column(df, ["Lev_Money_Positions_Short_All"])
    spread_col = _find_column(df, ["Lev_Money_Positions_Spread_All"])

    missing = []
    if not date_col: missing.append("date")
    if not market_col: missing.append("market")
    if not oi_col: missing.append("open_interest")
    if not long_col: missing.append("lev_long")
    if not short_col: missing.append("lev_short")
    if missing:
        raise ValueError(f"Puuttuvat sarakkeet CFTC-datasta: {missing}. Löydetyt: {list(df.columns[:10])}...")

    rows = []
    for ccy, search_str in _CONTRACT_SEARCH.items():
        # Tarkennettu haku: USD INDEX ei saa osua AUSTRALIAN DOLLAR jne.
        mask = df[market_col].str.upper().str.contains(search_str, na=False)
        subset = df[mask]

        # NZ DOLLAR voi osua myös "NEW ZEALAND DOLLAR", "NZ DOLLAR" jne.
        # USD INDEX ei saa osua muihin INDEX-nimiin
        if ccy == "USD":
            # Tarkennetaan: vain "USD INDEX" – ei esim. "S&P 500 INDEX"
            mask = df[market_col].str.upper().str.startswith("USD INDEX", na=False)
            subset = df[mask]

        if subset.empty:
            logger.warning("Valuuttaa %s ei löydy raportista (haku: '%s')", ccy, search_str)
            continue

        for _, row in subset.iterrows():
            try:
                report_date = pd.to_datetime(row[date_col]).date()
                spreading = float(row[spread_col]) if spread_col and pd.notna(row.get(spread_col)) else 0.0
                rows.append({
                    "report_date": report_date,
                    "currency": ccy,
                    "contract_name": str(row[market_col]).strip(),
                    "open_interest_total": float(row[oi_col]),
                    "lev_long": float(row[long_col]),
                    "lev_short": float(row[short_col]),
                    "lev_spreading": spreading,
                })
            except (ValueError, TypeError) as e:
                logger.warning("Virhe rivin parsinnassa (%s): %s", ccy, e)

    if rows:
        logger.info("Parsittu %d riviä, valuutat: %s", len(rows), sorted({r['currency'] for r in rows}))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


async def fetch_current_week() -> pd.DataFrame:
    """Hakee uusimman viikon COT-datan CFTC:n julkisesta CSV-API:sta."""
    logger.info("Haetaan viikkodata: %s", CFTC_CURRENT_URL)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(CFTC_CURRENT_URL)
        resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), low_memory=False)
    return _parse_raw_df(df)


async def fetch_year(year: int) -> pd.DataFrame:
    """
    Hakee yhden vuoden COT-historian CFTC:n ZIP-tiedostosta.
    Palauttaa parsitun DataFramen.
    """
    url = CFTC_HISTORY_URL_TEMPLATE.format(year=year)
    logger.info("Haetaan historiadata vuodelle %d: %s", year, url)

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    zip_bytes = io.BytesIO(resp.content)
    all_dfs = []

    with zipfile.ZipFile(zip_bytes) as zf:
        for name in zf.namelist():
            logger.debug("ZIP-tiedosto: %s", name)
            try:
                raw = zf.read(name)  # Luetaan kokonaan muistiin
                if name.lower().endswith(".xlsx"):
                    df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
                elif name.lower().endswith(".xls"):
                    df = pd.read_excel(io.BytesIO(raw), engine="xlrd")
                elif name.lower().endswith(".csv"):
                    df = pd.read_csv(io.BytesIO(raw), low_memory=False)
                else:
                    continue
                parsed = _parse_raw_df(df)
                if not parsed.empty:
                    all_dfs.append(parsed)
            except Exception as e:
                logger.warning("Tiedoston %s parsinta epäonnistui: %s", name, e)

    if not all_dfs:
        logger.warning("Vuodelta %d ei löytynyt dataa", year)
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["report_date", "currency"])
    logger.info("Vuosi %d: %d riviä ladattu", year, len(combined))
    return combined


async def fetch_history_all() -> pd.DataFrame:
    """Hakee koko historian CFTC_FIRST_YEAR:sta nykyvuoteen."""
    current_year = date.today().year
    all_dfs = []
    for year in range(CFTC_FIRST_YEAR, current_year + 1):
        try:
            df = await fetch_year(year)
            if not df.empty:
                all_dfs.append(df)
        except Exception as e:
            logger.error("Vuoden %d haku epäonnistui: %s", year, e)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["report_date", "currency"])
    combined = combined.sort_values("report_date")
    return combined


def parse_uploaded_file(content: bytes, filename: str) -> pd.DataFrame:
    """
    Parsii käyttäjän lataaman CSV- tai Excel-tiedoston.
    Tukee sekä CFTC:n standardimuotoa että yksinkertaistettua muotoa.
    """
    fname_lower = filename.lower()
    try:
        if fname_lower.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), low_memory=False)
        elif fname_lower.endswith((".xlsx", ".xls")):
            engine = "openpyxl" if fname_lower.endswith(".xlsx") else "xlrd"
            df = pd.read_excel(io.BytesIO(content), engine=engine)
        else:
            raise ValueError(f"Tuntematon tiedostomuoto: {filename}")
    except Exception as e:
        raise ValueError(f"Tiedoston lukeminen epäonnistui: {e}") from e

    return _parse_raw_df(df)
