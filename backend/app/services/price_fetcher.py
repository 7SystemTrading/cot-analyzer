"""
Hintadatan haku yfinancella ja SQLite-cache.
Haetaan päivittäiset OHLC-kynttilät forex-pareille verifiointia varten.
"""
import logging
from datetime import date, timedelta
from typing import List, Optional

import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session

from app.models import PriceData

logger = logging.getLogger(__name__)


def _pair_to_ticker(pair: str) -> str:
    """Muuntaa parin (esim. EURUSD) yfinance-tickeriksi (EURUSD=X)."""
    return f"{pair}=X"


def _get_cached(db: Session, pair: str, start: date, end: date) -> List[PriceData]:
    """Hae cachetettu hintadata tietokannasta."""
    return (
        db.query(PriceData)
        .filter(
            PriceData.pair == pair,
            PriceData.date >= start,
            PriceData.date <= end,
        )
        .order_by(PriceData.date)
        .all()
    )


def _save_to_cache(db: Session, pair: str, df: pd.DataFrame) -> int:
    """Tallenna yfinance-data SQLite-cacheen. Ohita duplikaatit."""
    saved = 0
    for idx, row in df.iterrows():
        d = idx.date() if hasattr(idx, 'date') else idx
        exists = (
            db.query(PriceData)
            .filter(PriceData.pair == pair, PriceData.date == d)
            .first()
        )
        if exists:
            continue
        record = PriceData(
            pair=pair,
            date=d,
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
        )
        db.add(record)
        saved += 1
    db.commit()
    return saved


def fetch_candles(
    db: Session,
    pair: str,
    start: date,
    end: date,
) -> List[dict]:
    """
    Hae päivittäinen OHLC-data parille aikavälillä.
    Käyttää SQLite-cachea – hakee yfinancesta vain puuttuvat.
    Palauttaa listan: [{"date", "open", "high", "low", "close"}, ...]
    """
    # Tarkista cache ensin
    cached = _get_cached(db, pair, start, end)
    cached_dates = {c.date for c in cached}

    # Tarvitaanko yfinance-haku?
    # Tarkistetaan onko viikonpäivistä (ma-pe) puuttuvia
    missing_days = []
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in cached_dates:  # ma=0 ... pe=4
            missing_days.append(d)
        d += timedelta(days=1)

    if missing_days and end <= date.today():
        # Hae yfinancesta koko aikaväli (yfinance palauttaa vain arkipäivät)
        ticker = _pair_to_ticker(pair)
        # yfinance end on exclusive → lisätään 1 päivä
        fetch_end = end + timedelta(days=1)
        try:
            logger.info("Haetaan hintadata: %s %s – %s", ticker, start, end)
            df = yf.download(
                ticker,
                start=start.isoformat(),
                end=fetch_end.isoformat(),
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
            if df is not None and not df.empty:
                # yfinance voi palauttaa MultiIndex-sarakkeet yhdelle tickerille
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                saved = _save_to_cache(db, pair, df)
                logger.info("Tallennettu %d uutta kynttilää: %s", saved, pair)
            else:
                logger.warning("Ei hintadataa: %s %s – %s", pair, start, end)
        except Exception as e:
            logger.error("Hintadatan haku epäonnistui %s: %s", pair, e)

    # Hae lopullinen data cachesta (voi sisältää juuri haetut)
    final = _get_cached(db, pair, start, end)
    return [
        {
            "date": c.date.isoformat(),
            "open": round(c.open, 5),
            "high": round(c.high, 5),
            "low": round(c.low, 5),
            "close": round(c.close, 5),
        }
        for c in final
    ]


def get_verification_week(report_date: date) -> tuple[date, date]:
    """
    Laskee verifiointiviikon alun ja lopun.
    report_date = tiistai (mittauspäivä)
    julkaisu = perjantai (+3 pv)
    verifiointi = seuraava ma (+6 pv) – pe (+10 pv)
    """
    # report_date on tiistai → perjantai = +3, seuraava maanantai = +6
    verify_start = report_date + timedelta(days=6)   # seuraava ma
    verify_end = report_date + timedelta(days=10)     # seuraava pe
    return verify_start, verify_end
