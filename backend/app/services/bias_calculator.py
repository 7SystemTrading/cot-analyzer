"""
COT Bias Dashboard -laskentamoottori.

Täysin erillinen laskentamalli z-score-pohjaisesta CurrencyScore-mallista.
Perustuu raaka Net % LF -arvoihin ja yksinkertaiseen strength index -erotukseen.

Kaavat:
  net_pos          = long - short
  net_pct_lf       = (net_pos / oi_lf) × 100
  strength_index   = (net_pct_lf_A − net_pct_lf_B) / 2     # väli −50…+50
  Δn               = net_pct_lf_w1 − net_pct_lf_w(n+1)      # n = 1…4

Bias-luokittelu (THRESHOLD = 25):
  STRONG LONG:  index > +THRESHOLD  AND  Δ1_A > 0  AND  Δ1_B < 0
  STRONG SHORT: index < −THRESHOLD  AND  Δ1_A < 0  AND  Δ1_B > 0
  NEUTRAL:      kaikki muu
"""
import logging
from datetime import date
from typing import Optional

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.config import CURRENCIES, DISPLAY_PAIRS
from app.models import RawReport

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 25.0


def _get_recent_weeks(db: Session, n_weeks: int = 5, ref_date: Optional[date] = None):
    """
    Hakee n uusinta raporttipäivää (tai n päivää ref_date:sta taaksepäin).
    Palauttaa listan päivämääristä uusimmasta vanhimpaan.
    """
    q = db.query(distinct(RawReport.report_date)).filter(
        RawReport.is_corrected == False  # noqa: E712
    )
    if ref_date:
        q = q.filter(RawReport.report_date <= ref_date)
    dates = [
        r[0]
        for r in q.order_by(RawReport.report_date.desc()).limit(n_weeks).all()
    ]
    return dates  # [uusin, ..., vanhin]


def _compute_net_pct_lf(db: Session, report_dates: list[date]) -> dict[date, dict[str, float]]:
    """
    Laskee Net % LF jokaiselle valuutalle jokaiselle viikolle.
    Palauttaa: { date: { "EUR": 12.5, "USD": -20.0, ... }, ... }
    """
    rows = (
        db.query(RawReport)
        .filter(
            RawReport.report_date.in_(report_dates),
            RawReport.is_corrected == False,  # noqa: E712
        )
        .all()
    )

    result: dict[date, dict[str, float]] = {}
    for r in rows:
        if r.currency not in CURRENCIES:
            continue
        # Spesifikaation mukaan OI_LF = long + short (ei spreading)
        oi_lf = r.lev_long + r.lev_short
        if oi_lf == 0:
            continue
        net_pos = r.lev_long - r.lev_short
        net_pct = (net_pos / oi_lf) * 100.0

        if r.report_date not in result:
            result[r.report_date] = {}
        result[r.report_date][r.currency] = net_pct

    return result


def _classify_pair(
    index: float, delta1_a: Optional[float], delta1_b: Optional[float], threshold: float
) -> str:
    """Luokittelee parin bias-tyypin."""
    if delta1_a is None or delta1_b is None:
        return "NEUTRAL"
    if index > threshold and delta1_a > 0 and delta1_b < 0:
        return "STRONG_LONG"
    if index < -threshold and delta1_a < 0 and delta1_b > 0:
        return "STRONG_SHORT"
    return "NEUTRAL"


def compute_bias_dashboard(
    db: Session,
    report_date: Optional[date] = None,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """
    Pääfunktio: laskee koko Bias Dashboard -näkymän datan.
    """
    # Hae 5 viikkoa
    weeks = _get_recent_weeks(db, n_weeks=5, ref_date=report_date)
    if not weeks:
        return {
            "report_date": None,
            "threshold": threshold,
            "currencies": [],
            "strong_long": [],
            "strong_short": [],
            "neutral_count": 0,
        }

    w1 = weeks[0]  # uusin
    weekly_data = _compute_net_pct_lf(db, weeks)

    # Valuuttakohtaiset tiedot
    currencies_out = []
    currency_current: dict[str, float] = weekly_data.get(w1, {})
    currency_deltas: dict[str, list[Optional[float]]] = {}

    for ccy in CURRENCIES:
        val_w1 = currency_current.get(ccy)
        deltas = []
        for i in range(1, 5):  # Δ1–Δ4
            if i < len(weeks):
                w_prev = weeks[i]
                val_prev = weekly_data.get(w_prev, {}).get(ccy)
                if val_w1 is not None and val_prev is not None:
                    deltas.append(round(val_w1 - val_prev, 2))
                else:
                    deltas.append(None)
            else:
                deltas.append(None)

        currency_deltas[ccy] = deltas
        currencies_out.append({
            "currency": ccy,
            "net_pct_lf": round(val_w1, 2) if val_w1 is not None else None,
            "delta_1": deltas[0],
            "delta_2": deltas[1],
            "delta_3": deltas[2],
            "delta_4": deltas[3],
        })

    # 28 standardiparia (forex-konventio: hierarkiajärjestys)
    pairs = DISPLAY_PAIRS
    strong_long = []
    strong_short = []
    neutral_count = 0

    for base, quote in pairs:
        val_a = currency_current.get(base)
        val_b = currency_current.get(quote)

        if val_a is None or val_b is None:
            neutral_count += 1
            continue

        index = round((val_a - val_b) / 2.0, 1)
        d1_a = currency_deltas.get(base, [None])[0]
        d1_b = currency_deltas.get(quote, [None])[0]

        # Tarkista täydet STRONG-ehdot (index + deltat)
        full_bias = _classify_pair(index, d1_a, d1_b, threshold)
        # confirmed = True kun sekä index- että delta-ehdot täyttyvät
        confirmed = full_bias in ("STRONG_LONG", "STRONG_SHORT")

        deltas_a = currency_deltas.get(base, [None, None, None, None])
        deltas_b = currency_deltas.get(quote, [None, None, None, None])

        pair_row = {
            "pair": f"{base}/{quote}",
            "base": base,
            "quote": quote,
            "strength_index": index,
            "bias": full_bias,
            "confirmed": confirmed,
            "net_pct_lf_base": round(val_a, 2),
            "net_pct_lf_quote": round(val_b, 2),
            "delta_1_base": deltas_a[0],
            "delta_1_quote": deltas_b[0],
            "delta_2_base": deltas_a[1] if len(deltas_a) > 1 else None,
            "delta_2_quote": deltas_b[1] if len(deltas_b) > 1 else None,
            "delta_3_base": deltas_a[2] if len(deltas_a) > 2 else None,
            "delta_3_quote": deltas_b[2] if len(deltas_b) > 2 else None,
            "delta_4_base": deltas_a[3] if len(deltas_a) > 3 else None,
            "delta_4_quote": deltas_b[3] if len(deltas_b) > 3 else None,
        }

        # Kaikki kynnyksen ylittävät parit näytetään taulukoissa
        if index > threshold:
            pair_row["bias"] = "STRONG_LONG" if confirmed else "LONG"
            strong_long.append(pair_row)
        elif index < -threshold:
            pair_row["bias"] = "STRONG_SHORT" if confirmed else "SHORT"
            strong_short.append(pair_row)
        else:
            neutral_count += 1

    # Järjestys: Long = suurin index ensin, Short = pienin index ensin
    strong_long.sort(key=lambda x: x["strength_index"], reverse=True)
    strong_short.sort(key=lambda x: x["strength_index"])

    return {
        "report_date": w1.isoformat() if w1 else None,
        "threshold": threshold,
        "currencies": currencies_out,
        "strong_long": strong_long,
        "strong_short": strong_short,
        "neutral_count": neutral_count,
    }
