"""
Hintadatan haku yfinancella ja SQLite-cache.
Haetaan 7 USD-pohjaista paria yfinancesta ja lasketaan niistä kaikki 28 cross-paria.
Tämä on sama logiikka kuin forex-brokereilla.
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

import numpy as np
import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session

from app.models import PriceData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# USD-pohjaiset parit (haetaan suoraan yfinancesta)
# ---------------------------------------------------------------------------
USD_DIRECT_TICKERS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "USDJPY": "USDJPY=X",
}

# ---------------------------------------------------------------------------
# Cross-parien laskentareseptit: (pari_A, pari_B, operaatio)
# Tyyppi "div": cross = A / B
# Tyyppi "mul": cross = A * B
# ---------------------------------------------------------------------------
CROSS_RECIPES = {
    # Tyyppi 1: molemmat XXX/USD → jako
    "EURGBP": ("EURUSD", "GBPUSD", "div"),
    "EURAUD": ("EURUSD", "AUDUSD", "div"),
    "EURNZD": ("EURUSD", "NZDUSD", "div"),
    "GBPAUD": ("GBPUSD", "AUDUSD", "div"),
    "GBPNZD": ("GBPUSD", "NZDUSD", "div"),
    "AUDNZD": ("AUDUSD", "NZDUSD", "div"),
    # Tyyppi 2: XXX/USD * USD/YYY → kerto
    "EURCAD": ("EURUSD", "USDCAD", "mul"),
    "EURCHF": ("EURUSD", "USDCHF", "mul"),
    "EURJPY": ("EURUSD", "USDJPY", "mul"),
    "GBPCAD": ("GBPUSD", "USDCAD", "mul"),
    "GBPCHF": ("GBPUSD", "USDCHF", "mul"),
    "GBPJPY": ("GBPUSD", "USDJPY", "mul"),
    "AUDCAD": ("AUDUSD", "USDCAD", "mul"),
    "AUDCHF": ("AUDUSD", "USDCHF", "mul"),
    "AUDJPY": ("AUDUSD", "USDJPY", "mul"),
    "NZDCAD": ("NZDUSD", "USDCAD", "mul"),
    "NZDCHF": ("NZDUSD", "USDCHF", "mul"),
    "NZDJPY": ("NZDUSD", "USDJPY", "mul"),
    # Tyyppi 3: molemmat USD/YYY → jako
    "CADCHF": ("USDCHF", "USDCAD", "div"),
    "CADJPY": ("USDJPY", "USDCAD", "div"),
    "CHFJPY": ("USDJPY", "USDCHF", "div"),
}


# ---------------------------------------------------------------------------
# Cache-funktiot (SQLite)
# ---------------------------------------------------------------------------

def _get_cached(db: Session, pair: str, start: date, end: date) -> List[PriceData]:
    return (
        db.query(PriceData)
        .filter(PriceData.pair == pair, PriceData.date >= start, PriceData.date <= end)
        .order_by(PriceData.date)
        .all()
    )


def _save_one(db: Session, pair: str, d: date, o: float, h: float, l: float, c: float):
    exists = db.query(PriceData).filter(PriceData.pair == pair, PriceData.date == d).first()
    if not exists:
        db.add(PriceData(pair=pair, date=d, open=o, high=h, low=l, close=c))


# ---------------------------------------------------------------------------
# Yfinance: hae 7 USD-pohjaista paria yhdellä kutsulla
# ---------------------------------------------------------------------------

def _fetch_usd_candles(db: Session, start: date, end: date) -> Dict[str, pd.DataFrame]:
    """
    Hakee 7 USD-parin päiväkynttilät yfinancesta.
    Palauttaa dict: {"EURUSD": DataFrame(Open,High,Low,Close), ...}
    Cachettaa samalla SQLiteen.
    """
    # Tarkista mitkä parit puuttuvat cachesta
    pairs_to_fetch = []
    for pair in USD_DIRECT_TICKERS:
        cached = _get_cached(db, pair, start, end)
        cached_dates = {c.date for c in cached}
        d = start
        while d <= end:
            if d.weekday() < 5 and d not in cached_dates:
                pairs_to_fetch.append(pair)
                break
            d += timedelta(days=1)

    # Hae puuttuvat yfinancesta
    if pairs_to_fetch and end <= date.today():
        tickers = [USD_DIRECT_TICKERS[p] for p in pairs_to_fetch]
        ticker_str = " ".join(tickers)
        fetch_end = end + timedelta(days=1)

        try:
            logger.info("Haetaan USD-pohjaiset parit yfinancesta: %s (%s – %s)", ticker_str, start, end)
            df = yf.download(
                ticker_str,
                start=start.isoformat(),
                end=fetch_end.isoformat(),
                interval="1d",
                progress=False,
                auto_adjust=True,
                group_by="ticker" if len(tickers) > 1 else None,
            )

            if df is not None and not df.empty:
                for pair, ticker in USD_DIRECT_TICKERS.items():
                    if pair not in pairs_to_fetch:
                        continue
                    try:
                        if len(tickers) == 1:
                            pair_df = df
                        else:
                            # MultiIndex: (Ticker, OHLC)
                            ticker_clean = ticker  # e.g. "EURUSD=X"
                            if ticker_clean in df.columns.get_level_values(0):
                                pair_df = df[ticker_clean]
                            else:
                                logger.warning("Ticker %s ei löydy yfinance-datasta", ticker_clean)
                                continue

                        if isinstance(pair_df.columns, pd.MultiIndex):
                            pair_df.columns = pair_df.columns.get_level_values(0)

                        pair_df = pair_df.dropna(subset=["Close"])
                        for idx, row in pair_df.iterrows():
                            d = idx.date() if hasattr(idx, 'date') else idx
                            _save_one(db, pair, d, float(row["Open"]), float(row["High"]),
                                      float(row["Low"]), float(row["Close"]))
                        logger.info("Tallennettu: %s (%d kynttilää)", pair, len(pair_df))
                    except Exception as e:
                        logger.warning("Parin %s parsinta epäonnistui: %s", pair, e)

                db.commit()
            else:
                logger.warning("Yfinance palautti tyhjän tuloksen")
        except Exception as e:
            logger.error("Yfinance-haku epäonnistui: %s", e)

    # Palauta kaikki USD-parit cachesta DataFrameina
    result = {}
    for pair in USD_DIRECT_TICKERS:
        cached = _get_cached(db, pair, start, end)
        if cached:
            rows = [{"date": c.date, "Open": c.open, "High": c.high, "Low": c.low, "Close": c.close}
                    for c in cached]
            pdf = pd.DataFrame(rows).set_index("date")
            result[pair] = pdf
    return result


# ---------------------------------------------------------------------------
# Cross-parien laskenta USD-pareista
# ---------------------------------------------------------------------------

def _calculate_cross(pair: str, usd_data: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    """
    Laskee cross-parin OHLC USD-pohjaisista pareista.
    Palauttaa DataFramen tai None jos puuttuu dataa.
    """
    if pair in USD_DIRECT_TICKERS:
        return usd_data.get(pair)

    recipe = CROSS_RECIPES.get(pair)
    if not recipe:
        logger.warning("Ei reseptiä parille %s", pair)
        return None

    pair_a, pair_b, op = recipe
    df_a = usd_data.get(pair_a)
    df_b = usd_data.get(pair_b)

    if df_a is None or df_b is None or df_a.empty or df_b.empty:
        logger.warning("Puuttuvaa USD-dataa cross-laskentaan: %s (tarvitaan %s, %s)", pair, pair_a, pair_b)
        return None

    # Yhdistä päivämäärällä (vain yhteiset päivät)
    merged = df_a.join(df_b, lsuffix="_a", rsuffix="_b", how="inner")
    if merged.empty:
        return None

    result_rows = []
    for idx, row in merged.iterrows():
        if op == "mul":
            cross_open = row["Open_a"] * row["Open_b"]
            cross_close = row["Close_a"] * row["Close_b"]
            # High/Low: approx (ei tiedä intraday-ajoitusta)
            cross_high = max(row["High_a"] * row["High_b"], row["High_a"] * row["Low_b"],
                             row["Low_a"] * row["High_b"])
            cross_low = min(row["Low_a"] * row["Low_b"], row["Low_a"] * row["High_b"],
                            row["High_a"] * row["Low_b"])
        else:  # div
            if row["Open_b"] == 0 or row["Close_b"] == 0:
                continue
            cross_open = row["Open_a"] / row["Open_b"]
            cross_close = row["Close_a"] / row["Close_b"]
            # High/Low: A_high / B_low ≈ max, A_low / B_high ≈ min
            cross_high = max(row["High_a"] / row["Low_b"], row["Low_a"] / row["High_b"],
                             row["High_a"] / row["High_b"])
            cross_low = min(row["Low_a"] / row["High_b"], row["High_a"] / row["Low_b"],
                            row["Low_a"] / row["Low_b"])

        result_rows.append({
            "date": idx,
            "Open": cross_open,
            "High": cross_high,
            "Low": cross_low,
            "Close": cross_close,
        })

    if not result_rows:
        return None
    return pd.DataFrame(result_rows).set_index("date")


# ---------------------------------------------------------------------------
# Julkinen API
# ---------------------------------------------------------------------------

def fetch_candles(db: Session, pair: str, start: date, end: date) -> List[dict]:
    """
    Hae päivittäinen OHLC-data parille aikavälillä.
    1. Tarkista cache
    2. Jos puuttuu: hae USD-parit yfinancesta → laske cross-parit → cacheta
    3. Palauta lista dicttejä
    """
    # Tarkista cache ensin
    cached = _get_cached(db, pair, start, end)
    expected_days = sum(1 for d_offset in range((end - start).days + 1)
                        if (start + timedelta(days=d_offset)).weekday() < 5)

    if len(cached) >= expected_days:
        # Kaikki päivät cachessa
        return [{"date": c.date.isoformat(), "open": round(c.open, 5),
                 "high": round(c.high, 5), "low": round(c.low, 5), "close": round(c.close, 5)}
                for c in cached]

    # Puuttuu dataa → hae USD-parit ja laske kaikki
    usd_data = _fetch_usd_candles(db, start, end)

    if pair in USD_DIRECT_TICKERS:
        # USD-pari on jo cachessa _fetch_usd_candles:n jälkeen
        pass
    else:
        # Laske cross-pari ja tallenna cacheen
        cross_df = _calculate_cross(pair, usd_data)
        if cross_df is not None and not cross_df.empty:
            for idx, row in cross_df.iterrows():
                d = idx if isinstance(idx, date) else idx
                _save_one(db, pair, d, float(row["Open"]), float(row["High"]),
                          float(row["Low"]), float(row["Close"]))
            db.commit()
            logger.info("Cross-pari %s laskettu ja tallennettu (%d kynttilää)", pair, len(cross_df))

    # Hae lopullinen tulos cachesta
    final = _get_cached(db, pair, start, end)
    return [{"date": c.date.isoformat(), "open": round(c.open, 5),
             "high": round(c.high, 5), "low": round(c.low, 5), "close": round(c.close, 5)}
            for c in final]


def fetch_all_pairs_candles(db: Session, pairs: List[str], start: date, end: date) -> Dict[str, List[dict]]:
    """
    Hae OHLC-data KAIKILLE pareille kerralla (optimoitu: 1 yfinance-kutsu).
    Palauttaa dict: {"EURUSD": [{date, open, high, low, close}, ...], ...}
    """
    # Hae USD-parit kerran
    usd_data = _fetch_usd_candles(db, start, end)

    result = {}
    for pair in pairs:
        # Tarkista cache
        cached = _get_cached(db, pair, start, end)
        expected_days = sum(1 for d_offset in range((end - start).days + 1)
                            if (start + timedelta(days=d_offset)).weekday() < 5)

        if len(cached) >= expected_days:
            result[pair] = [{"date": c.date.isoformat(), "open": round(c.open, 5),
                             "high": round(c.high, 5), "low": round(c.low, 5), "close": round(c.close, 5)}
                            for c in cached]
            continue

        # Laske ja cacheta
        if pair not in USD_DIRECT_TICKERS:
            cross_df = _calculate_cross(pair, usd_data)
            if cross_df is not None and not cross_df.empty:
                for idx, row in cross_df.iterrows():
                    _save_one(db, pair, idx, float(row["Open"]), float(row["High"]),
                              float(row["Low"]), float(row["Close"]))
                db.commit()

        final = _get_cached(db, pair, start, end)
        result[pair] = [{"date": c.date.isoformat(), "open": round(c.open, 5),
                         "high": round(c.high, 5), "low": round(c.low, 5), "close": round(c.close, 5)}
                        for c in final]

    return result


def get_verification_week(report_date: date) -> tuple[date, date]:
    """
    Laskee verifiointiviikon alun ja lopun.
    report_date = tiistai (mittauspäivä)
    julkaisu = perjantai (+3 pv)
    verifiointi = seuraava ma (+6 pv) – pe (+10 pv)
    """
    verify_start = report_date + timedelta(days=6)
    verify_end = report_date + timedelta(days=10)
    return verify_start, verify_end
