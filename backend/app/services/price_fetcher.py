"""
COT Dashboard v2 – Price data fetcher and cache.
Fetches weekly closing prices from yfinance for divergence calculations.
Fetches 7 USD-base pairs and computes all 28 cross-pairs from them.
"""
import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from app.models import PriceData

logger = logging.getLogger(__name__)

# Yahoo Finance tickers for USD-base pairs
_USD_TICKERS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "USDJPY": "USDJPY=X",
}

_TIMEOUT = 30  # seconds


def _get_usd_rate(currency: str, usd_prices: dict[str, float]) -> Optional[float]:
    """Return price of currency vs USD (base/USD or USD/base)."""
    if f"{currency}USD" in usd_prices:
        return usd_prices[f"{currency}USD"]
    if f"USD{currency}" in usd_prices:
        v = usd_prices[f"USD{currency}"]
        return 1.0 / v if v else None
    return None


def _cross_price(base: str, quote: str, usd_prices: dict[str, float]) -> Optional[float]:
    """Compute cross-pair price from USD rates."""
    if base == "USD":
        usd_quote = usd_prices.get(f"USD{quote}")
        return usd_quote
    if quote == "USD":
        base_usd = usd_prices.get(f"{base}USD")
        return base_usd

    base_usd  = _get_usd_rate(base, usd_prices)
    quote_usd = _get_usd_rate(quote, usd_prices)
    if base_usd and quote_usd and quote_usd != 0:
        return base_usd / quote_usd
    return None


def fetch_weekly_closes(
    pair: str,
    start: date,
    end: date,
    db: Session,
) -> list[float]:
    """
    Return list of weekly closing prices for a pair between start and end.
    Checks DB cache first; fetches from yfinance if needed.
    """
    # Try cache
    cached = (
        db.query(PriceData.date, PriceData.close)
        .filter(PriceData.pair == pair, PriceData.date >= start, PriceData.date <= end)
        .order_by(PriceData.date)
        .all()
    )
    if cached:
        return [float(r.close) for r in cached]

    # Fetch from yfinance
    base  = pair[:3]
    quote = pair[3:]

    try:
        tickers = list(_USD_TICKERS.values())
        data = yf.download(
            tickers,
            start=str(start - timedelta(days=7)),
            end=str(end + timedelta(days=1)),
            interval="1wk",
            progress=False,
            timeout=_TIMEOUT,
        )
        if data.empty:
            return []

        closes = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)

        results = []
        for _, row in closes.iterrows():
            usd_prices: dict[str, float] = {}
            for pair_name, ticker in _USD_TICKERS.items():
                val = row.get(ticker)
                if val and not pd.isna(val):
                    usd_prices[pair_name] = float(val)

            price = _cross_price(base, quote, usd_prices)
            if price:
                row_date = row.name.date() if hasattr(row.name, "date") else row.name
                results.append((row_date, price))

                # Cache
                existing = (
                    db.query(PriceData)
                    .filter(PriceData.pair == pair, PriceData.date == row_date)
                    .first()
                )
                if not existing:
                    db.add(PriceData(
                        pair=pair, date=row_date,
                        open=price, high=price, low=price, close=price,
                    ))

        db.commit()
        return [p for _, p in sorted(results) if start <= _ <= end]

    except Exception as e:
        logger.warning("yfinance error for %s: %s", pair, e)
        return []


def get_recent_weekly_closes(
    pair: str,
    report_date: date,
    weeks: int,
    db: Session,
) -> list[float]:
    """
    Return the last `weeks` weekly closes ending at report_date.
    Used for divergence slope calculation.
    """
    end   = report_date
    start = report_date - timedelta(weeks=weeks + 2)
    closes = fetch_weekly_closes(pair, start, end, db)
    return closes[-weeks:] if len(closes) >= weeks else closes
