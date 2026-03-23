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
    ComponentAnalysisResponse,
    ComponentHitRates,
    VerificationPairRow,
    VerificationResponse,
    VerificationStatsResponse,
    VerificationWeekSummary,
)
from app.services.price_fetcher import fetch_candles, get_verification_period, get_verification_week

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
    horizon: int = Query(1, ge=1, le=8, description="Verifiointihorisontti viikkoina (1/2/4)"),
    db: Session = Depends(get_db),
):
    """Verifiointi: vertaa COT-biasta hintakehitykseen valitulla horisontilla."""

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

    # Verifiointiperiodi (1/2/4 viikkoa)
    verify_start, verify_end = get_verification_period(rd, horizon)
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

    # Hae kynttilät vain ei-neutraaleille pareille (keventää hakua)
    non_neutral_pairs = [pr for pr in pair_rows if _is_bullish(pr.bias_label or "") is not None]
    neutral_pairs = [pr for pr in pair_rows if _is_bullish(pr.bias_label or "") is None]

    # Hae hintadata kaikille ei-neutraaleille pareille kerralla (1 yfinance-kutsu)
    if non_neutral_pairs and verify_end <= date.today():
        from app.services.price_fetcher import fetch_all_pairs_candles
        pair_names = [pr.pair for pr in non_neutral_pairs]
        all_candles = fetch_all_pairs_candles(db, pair_names, verify_start, verify_end)
    else:
        all_candles = {}

    # Rakenna verifiointi
    verifications = []
    for pr in non_neutral_pairs:
        candles = all_candles.get(pr.pair, [])
        v = _build_pair_verification(pr, candles)
        verifications.append(v)

    # Neutraalit parit: ei hintadataa, vain bias-tiedot
    for pr in neutral_pairs:
        v = _build_pair_verification(pr, [])
        verifications.append(v)

    # Järjestä takaisin scoren mukaan
    verifications.sort(key=lambda v: v.pair_score, reverse=True)

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
    horizon: int = Query(1, ge=1, le=8, description="Verifiointihorisontti viikkoina"),
    db: Session = Depends(get_db),
):
    """Kumulatiivinen osumisprosentti usean viikon yli, valitulla horisontilla."""

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
        verify_start, verify_end = get_verification_period(rd, horizon)

        # Ohita jos verifiointiviikko on tulevaisuudessa
        if verify_end > date.today():
            continue

        pair_rows = (
            db.query(PairMetrics)
            .filter(PairMetrics.report_date == rd)
            .filter(PairMetrics.pair_score.isnot(None))
            .all()
        )

        # Hae vain ei-neutraalit parit + kerralla (1 yfinance-kutsu per viikko)
        non_neutral = [(pr, _is_bullish(pr.bias_label or "")) for pr in pair_rows]
        non_neutral = [(pr, bull) for pr, bull in non_neutral if bull is not None]

        if non_neutral:
            from app.services.price_fetcher import fetch_all_pairs_candles
            pair_names = [pr.pair for pr, _ in non_neutral]
            all_candles = fetch_all_pairs_candles(db, pair_names, verify_start, verify_end)
        else:
            all_candles = {}

        week_hits = []
        for pr, is_bull in non_neutral:
            candles = all_candles.get(pr.pair, [])
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


# ---------------------------------------------------------------------------
# Komponenttianalyysi: selvitä mikä komponentti (A/B/C/D) oikeasti ennustaa
# ---------------------------------------------------------------------------

EXTREME_THRESHOLD = 1.5  # |z| > 1.5 = äärimmäinen

# Analysoitavat komponentit: nimi, DB-sarakkeet base/quote
_COMPONENT_DEFS = [
    ("A", "Positioning (taso)", "z_current"),
    ("B", "1vk momentum", "z_delta_1w"),
    ("C", "4vk momentum", "z_delta_4w"),
    ("D", "OI-osallistuminen", "z_oi_delta"),
]


def _safe_hr(correct_list):
    if not correct_list:
        return None
    return round(sum(correct_list) / len(correct_list), 3)


@router.get("/component-analysis", response_model=ComponentAnalysisResponse)
def get_component_analysis(
    weeks: int = Query(52, ge=10, le=260),
    horizon: int = Query(1, ge=1, le=8, description="Verifiointihorisontti viikkoina"),
    db: Session = Depends(get_db),
):
    """
    Analysoi jokainen CurrencyScore-komponentti (A/B/C/D) erikseen
    ja testaa sekä trendinmukaista että kontraarista tulkintaa.
    """
    from app.services.price_fetcher import fetch_all_pairs_candles, get_verification_period
    from app.config import DISPLAY_PAIRS

    # Hae viimeisimmät N raporttipäivää
    report_dates = (
        db.query(CurrencyMetrics.report_date)
        .filter(CurrencyMetrics.currency_score.isnot(None))
        .distinct()
        .order_by(CurrencyMetrics.report_date.desc())
        .limit(weeks)
        .all()
    )
    report_dates = [r[0] for r in reversed(report_dates)]

    if not report_dates:
        return ComponentAnalysisResponse(horizon_weeks=horizon, analysis_weeks=weeks)

    # Kerää data: per komponentti, per horisontti
    # comp_name → {trend: [bool], contrarian: [bool], extreme_trend: [bool], extreme_contrarian: [bool]}
    comp_results = {}
    for comp_key, comp_label, _ in _COMPONENT_DEFS:
        comp_results[comp_key] = {
            "label": comp_label, "trend": [], "contrarian": [],
            "extreme_trend": [], "extreme_contrarian": [],
        }
    # Yhdistelmä B+C
    comp_results["B+C"] = {
        "label": "Momentum (B+C)", "trend": [], "contrarian": [],
        "extreme_trend": [], "extreme_contrarian": [],
    }
    # Nykyinen komposiitti
    comp_results["Composite"] = {
        "label": "Nykyinen malli", "trend": [], "contrarian": [],
        "extreme_trend": [], "extreme_contrarian": [],
    }

    for rd in report_dates:
        verify_start, verify_end = get_verification_period(rd, horizon)
        if verify_end > date.today():
            continue

        # Hae valuuttametriikat tälle viikolle
        ccy_rows = {
            cm.currency: cm
            for cm in db.query(CurrencyMetrics)
            .filter(CurrencyMetrics.report_date == rd)
            .filter(CurrencyMetrics.currency_score.isnot(None))
            .all()
        }
        if len(ccy_rows) < 2:
            continue

        # Hae pari-metriikat
        pair_rows = {
            pm.pair: pm
            for pm in db.query(PairMetrics)
            .filter(PairMetrics.report_date == rd)
            .filter(PairMetrics.pair_score.isnot(None))
            .all()
        }

        # Hae hintadata kaikille pareille kerralla
        all_pair_names = list(pair_rows.keys())
        if not all_pair_names:
            continue
        all_candles = fetch_all_pairs_candles(db, all_pair_names, verify_start, verify_end)

        # Analysoi jokainen pari
        for base, quote in DISPLAY_PAIRS:
            pair_name = f"{base}{quote}"
            candles = all_candles.get(pair_name, [])
            if not candles or len(candles) < 2:
                continue

            week_open = candles[0]["open"]
            week_close = candles[-1]["close"]
            if week_open == 0:
                continue
            went_up = week_close > week_open

            base_cm = ccy_rows.get(base)
            quote_cm = ccy_rows.get(quote)
            if not base_cm or not quote_cm:
                continue

            # Per komponentti: laske parin z-score erotus = base_z - quote_z
            for comp_key, comp_label, db_field in _COMPONENT_DEFS:
                base_z = getattr(base_cm, db_field, None)
                quote_z = getattr(quote_cm, db_field, None)
                if base_z is None or quote_z is None:
                    continue

                pair_z = base_z - quote_z
                if pair_z == 0:
                    continue

                is_positive = pair_z > 0
                is_extreme = abs(pair_z) > EXTREME_THRESHOLD * 2  # parin z on kahden valuutan erotus

                # Trend: ennusta samaan suuntaan kuin z
                trend_correct = went_up if is_positive else not went_up
                comp_results[comp_key]["trend"].append(trend_correct)
                comp_results[comp_key]["contrarian"].append(not trend_correct)

                if is_extreme:
                    comp_results[comp_key]["extreme_trend"].append(trend_correct)
                    comp_results[comp_key]["extreme_contrarian"].append(not trend_correct)

            # B+C yhdistelmä
            base_b = getattr(base_cm, "z_delta_1w", None)
            base_c = getattr(base_cm, "z_delta_4w", None)
            quote_b = getattr(quote_cm, "z_delta_1w", None)
            quote_c = getattr(quote_cm, "z_delta_4w", None)
            if all(v is not None for v in [base_b, base_c, quote_b, quote_c]):
                bc_pair = (base_b + base_c) - (quote_b + quote_c)
                if bc_pair != 0:
                    trend_correct = (went_up if bc_pair > 0 else not went_up)
                    comp_results["B+C"]["trend"].append(trend_correct)
                    comp_results["B+C"]["contrarian"].append(not trend_correct)
                    if abs(bc_pair) > EXTREME_THRESHOLD * 2:
                        comp_results["B+C"]["extreme_trend"].append(trend_correct)
                        comp_results["B+C"]["extreme_contrarian"].append(not trend_correct)

            # Komposiitti (nykyinen malli)
            pm = pair_rows.get(pair_name)
            if pm and pm.pair_score is not None and pm.pair_score != 0:
                trend_correct = went_up if pm.pair_score > 0 else not went_up
                comp_results["Composite"]["trend"].append(trend_correct)
                comp_results["Composite"]["contrarian"].append(not trend_correct)
                if abs(pm.pair_score) > 1.5:
                    comp_results["Composite"]["extreme_trend"].append(trend_correct)
                    comp_results["Composite"]["extreme_contrarian"].append(not trend_correct)

    # Muodosta vastaus
    components = []
    for key in ["A", "B", "C", "D", "B+C", "Composite"]:
        r = comp_results[key]
        components.append(ComponentHitRates(
            component=key,
            label=r["label"],
            trend_hit_rate=_safe_hr(r["trend"]),
            contrarian_hit_rate=_safe_hr(r["contrarian"]),
            extreme_trend_hr=_safe_hr(r["extreme_trend"]),
            extreme_contrarian_hr=_safe_hr(r["extreme_contrarian"]),
            sample_count=len(r["trend"]),
            extreme_count=len(r["extreme_trend"]),
        ))

    # Paras trendinmukainen ja kontraarinen
    trend_best = max(
        [c for c in components if c.trend_hit_rate is not None],
        key=lambda c: c.trend_hit_rate,
        default=None,
    )
    contrarian_best = max(
        [c for c in components if c.contrarian_hit_rate is not None],
        key=lambda c: c.contrarian_hit_rate,
        default=None,
    )

    return ComponentAnalysisResponse(
        horizon_weeks=horizon,
        analysis_weeks=len(report_dates),
        components=components,
        best_trend=trend_best.component if trend_best else None,
        best_contrarian=contrarian_best.component if contrarian_best else None,
    )
