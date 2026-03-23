"""
Verifiointi-endpoint: vertaa COT-biastuloksia todelliseen hintakehitykseen.
Hakee seuraavan viikon OHLC-kynttilät yfinancesta ja laskee osumisprosentit.
"""
import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CurrencyMetrics, PairMetrics
from app.schemas import (
    CandleOut,
    VerificationPairRow,
    VerificationResponse,
    VerificationStatsResponse,
    VerificationWeekSummary,
)
from app.services.price_fetcher import fetch_candles, get_verification_week

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])
logger = logging.getLogger(__name__)


def _is_bullish(label: str) -> Optional[bool]:
    """True = bullish, False = bearish, None = neutraali."""
    l = label.lower()
    if "nouseva" in l:
        return True
    if "laskeva" in l:
        return False
    return None


def _build_pair_verification(
    pair_row,
    candles: List[dict],
) -> VerificationPairRow:
    """Rakentaa yhden parin verifioinnin kynttilädatasta."""
    pair = pair_row.pair
    bias_label = pair_row.bias_label or "Neutraali"
    pair_score = pair_row.pair_score or 0.0
    is_bull = _is_bullish(bias_label)

    if not candles:
        return VerificationPairRow(
            pair=pair,
            bias_label=bias_label,
            pair_score=round(pair_score, 2),
            candles=[],
        )

    candle_out = [CandleOut(**c) for c in candles]

    # Päiväkohtaiset muutokset: close vs edellinen close
    daily_changes = []
    daily_correct = []
    prev_close = candles[0]["open"]  # ensimmäisen päivän vertailukohtana open

    for c in candles:
        if prev_close and prev_close != 0:
            change_pct = round((c["close"] - prev_close) / prev_close * 100, 3)
        else:
            change_pct = None
        daily_changes.append(change_pct)

        if is_bull is not None and change_pct is not None:
            if is_bull:
                daily_correct.append(change_pct > 0)
            else:
                daily_correct.append(change_pct < 0)
        else:
            daily_correct.append(None)

        prev_close = c["close"]

    # Viikkoyhteenveto
    week_open = candles[0]["open"]
    week_close = candles[-1]["close"]
    if week_open and week_open != 0:
        week_change_pct = round((week_close - week_open) / week_open * 100, 3)
    else:
        week_change_pct = None

    direction = "up" if week_change_pct and week_change_pct > 0 else "down" if week_change_pct and week_change_pct < 0 else None

    # Viikko-osuma
    if is_bull is not None and direction is not None:
        if is_bull:
            week_correct = direction == "up"
        else:
            week_correct = direction == "down"
    else:
        week_correct = None

    # Päiväkohtainen hit rate
    valid_days = [d for d in daily_correct if d is not None]
    daily_hr = round(sum(valid_days) / len(valid_days), 2) if valid_days else None

    return VerificationPairRow(
        pair=pair,
        bias_label=bias_label,
        pair_score=round(pair_score, 2),
        candles=candle_out,
        daily_changes_pct=daily_changes,
        daily_bias_correct=daily_correct,
        week_open=round(week_open, 5) if week_open else None,
        week_close=round(week_close, 5) if week_close else None,
        week_change_pct=week_change_pct,
        direction=direction,
        week_bias_correct=week_correct,
        daily_hit_rate=daily_hr,
    )


@router.get("", response_model=VerificationResponse)
def get_verification(
    report_date: Optional[str] = Query(None, description="YYYY-MM-DD, oletuksena uusin"),
    db: Session = Depends(get_db),
):
    """Verifiointi: vertaa COT-biasta seuraavan viikon hintakehitykseen."""

    # Raporttipäivä
    if report_date:
        try:
            rd = date.fromisoformat(report_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Virheellinen päivämäärä")
    else:
        latest = (
            db.query(PairMetrics.report_date)
            .filter(PairMetrics.pair_score.isnot(None))
            .order_by(PairMetrics.report_date.desc())
            .first()
        )
        if not latest:
            return VerificationResponse()
        rd = latest[0]

    # Verifiointiviikko
    verify_start, verify_end = get_verification_week(rd)
    publish_date = rd + timedelta(days=3)

    # Hae kaikki parit tälle viikolle
    pair_rows = (
        db.query(PairMetrics)
        .filter(PairMetrics.report_date == rd)
        .filter(PairMetrics.pair_score.isnot(None))
        .order_by(PairMetrics.pair_score.desc())
        .all()
    )

    if not pair_rows:
        return VerificationResponse(
            report_date=rd,
            publish_date=publish_date,
            verification_start=verify_start,
            verification_end=verify_end,
        )

    # Hae kynttilät ja rakenna verifiointi jokaiselle parille
    verifications = []
    for pr in pair_rows:
        candles = fetch_candles(db, pr.pair, verify_start, verify_end)
        v = _build_pair_verification(pr, candles)
        verifications.append(v)

    # Kokonaisstatistiikka
    week_correct = [v.week_bias_correct for v in verifications if v.week_bias_correct is not None]
    daily_all = []
    strong_correct = []
    mild_correct = []

    for v in verifications:
        is_bull = _is_bullish(v.bias_label)
        if is_bull is None:
            continue

        valid_daily = [d for d in v.daily_bias_correct if d is not None]
        daily_all.extend(valid_daily)

        if v.week_bias_correct is not None:
            if abs(v.pair_score) >= 1.25:
                strong_correct.append(v.week_bias_correct)
            elif abs(v.pair_score) >= 0.5:
                mild_correct.append(v.week_bias_correct)

    total_neutral = sum(1 for v in verifications if _is_bullish(v.bias_label) is None)

    return VerificationResponse(
        report_date=rd,
        publish_date=publish_date,
        verification_start=verify_start,
        verification_end=verify_end,
        pairs=verifications,
        hit_rate_week=round(sum(week_correct) / len(week_correct), 3) if week_correct else None,
        hit_rate_daily=round(sum(daily_all) / len(daily_all), 3) if daily_all else None,
        hit_rate_strong=round(sum(strong_correct) / len(strong_correct), 3) if strong_correct else None,
        hit_rate_mild=round(sum(mild_correct) / len(mild_correct), 3) if mild_correct else None,
        total_evaluated=len(week_correct),
        total_neutral=total_neutral,
    )


@router.get("/stats", response_model=VerificationStatsResponse)
def get_verification_stats(
    weeks: int = Query(26, ge=1, le=260),
    db: Session = Depends(get_db),
):
    """Kumulatiivinen osumisprosentti usean viikon yli."""

    # Hae viimeisimmät N viikkoa joille on pair_metrics
    report_dates = (
        db.query(PairMetrics.report_date)
        .filter(PairMetrics.pair_score.isnot(None))
        .distinct()
        .order_by(PairMetrics.report_date.desc())
        .limit(weeks)
        .all()
    )
    report_dates = [r[0] for r in reversed(report_dates)]

    if not report_dates:
        return VerificationStatsResponse()

    all_week_correct = []
    all_daily_correct = []
    all_strong = []
    all_mild = []
    by_week = []

    for rd in report_dates:
        verify_start, verify_end = get_verification_week(rd)

        # Ohita jos verifiointiviikko on tulevaisuudessa
        if verify_end > date.today():
            continue

        pair_rows = (
            db.query(PairMetrics)
            .filter(PairMetrics.report_date == rd)
            .filter(PairMetrics.pair_score.isnot(None))
            .all()
        )

        week_hits = []
        for pr in pair_rows:
            is_bull = _is_bullish(pr.bias_label or "")
            if is_bull is None:
                continue

            candles = fetch_candles(db, pr.pair, verify_start, verify_end)
            if not candles:
                continue

            week_open = candles[0]["open"]
            week_close = candles[-1]["close"]
            if week_open == 0:
                continue

            went_up = week_close > week_open
            correct = went_up if is_bull else not went_up
            week_hits.append(correct)
            all_week_correct.append(correct)

            if abs(pr.pair_score) >= 1.25:
                all_strong.append(correct)
            elif abs(pr.pair_score) >= 0.5:
                all_mild.append(correct)

            # Päiväkohtainen
            prev_close = candles[0]["open"]
            for c in candles:
                if prev_close != 0:
                    d_correct = (c["close"] > prev_close) if is_bull else (c["close"] < prev_close)
                    all_daily_correct.append(d_correct)
                prev_close = c["close"]

        hr = round(sum(week_hits) / len(week_hits), 3) if week_hits else None
        by_week.append(VerificationWeekSummary(
            report_date=rd,
            hit_rate=hr,
            pairs_evaluated=len(week_hits),
        ))

    return VerificationStatsResponse(
        weeks_analyzed=len(by_week),
        week_hit_rate=round(sum(all_week_correct) / len(all_week_correct), 3) if all_week_correct else None,
        daily_hit_rate=round(sum(all_daily_correct) / len(all_daily_correct), 3) if all_daily_correct else None,
        strong_bias_hit_rate=round(sum(all_strong) / len(all_strong), 3) if all_strong else None,
        mild_bias_hit_rate=round(sum(all_mild) / len(all_mild), 3) if all_mild else None,
        by_week=by_week,
    )
