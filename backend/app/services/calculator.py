"""
Laskentamoottori – CurrencyScore ja PairScore.

Kaava:
  net_position        = lev_long - lev_short
  oi_lf               = lev_long + lev_short + lev_spreading
  net_percent_lf      = net_position / oi_lf
  oi_lf_ratio         = oi_lf / open_interest_total

  delta_1w            = net_percent_lf[t] - net_percent_lf[t-1]
  delta_4w            = net_percent_lf[t] - net_percent_lf[t-4]
  oi_delta_4w         = oi_lf_ratio[t] - oi_lf_ratio[t-4]

  A = zscore(net_percent_lf, 26w)
  B = zscore(delta_1w, 26w)
  C = zscore(delta_4w, 26w)
  D = zscore(oi_delta_4w, 26w)

  CurrencyScore = 0.45*A + 0.25*B + 0.20*C + 0.10*D
  PairScore(base/quote) = CurrencyScore(base) - CurrencyScore(quote)
"""
import itertools
import logging
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sqlalchemy.orm import Session

from app.config import (
    CURRENCIES,
    DEFAULT_CURRENCY_THRESHOLDS,
    DEFAULT_PAIR_THRESHOLDS,
    DEFAULT_WEIGHTS,
    DISPLAY_PAIRS,
    FALLBACK_WEIGHTS_SHORT,
    MIN_HISTORY_WEEKS,
    PERCENTILE_WINDOW,
    ZSCORE_WINDOW,
)
from app.models import CurrencyMetrics, PairMetrics, RawReport
from app.services.commentary import generate_currency_commentary, generate_pair_commentary

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Apufunktiot
# ---------------------------------------------------------------------------

def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    """
    Laskee lookback z-scoren: ikkuna t-window...t-1 (ei sisällä t:tä).
    Näin ääriarvo ei kompressoi omaa z-scoretaan.
    """
    shifted = series.shift(1)
    roll_mean = shifted.rolling(window=window, min_periods=window).mean()
    roll_std = shifted.rolling(window=window, min_periods=window).std(ddof=1)
    z = (series - roll_mean) / roll_std.replace(0, np.nan)
    return z


def _percentile_rank(series: pd.Series, window: int) -> pd.Series:
    """
    Laskee vierivän percentile-rankin (0–100).
    Kuinka monta % historiallisista arvoista nykyinen ylittää.
    """
    def _prank(vals):
        clean = vals[~np.isnan(vals)]
        if len(clean) < 2:
            return np.nan
        ranks = rankdata(clean)
        return (ranks[-1] - 1) / (len(clean) - 1) * 100

    return series.rolling(window=window, min_periods=2).apply(_prank, raw=True)


def _currency_bias_label(score: float, A: float, B: float, C: float) -> str:
    t = DEFAULT_CURRENCY_THRESHOLDS
    # NaN-safe: True vain jos arvo on olemassa ja oikean puoleinen
    a_pos = A > 0 if not pd.isna(A) else False
    a_neg = A < 0 if not pd.isna(A) else False
    b_pos = B > 0 if not pd.isna(B) else False
    b_neg = B < 0 if not pd.isna(B) else False
    c_pos = C > 0 if not pd.isna(C) else False
    c_neg = C < 0 if not pd.isna(C) else False

    if score >= t.strong_bull and a_pos and (b_pos or c_pos):
        return "Vahva nouseva"
    elif score >= t.mild_bull:
        return "Lievästi nouseva"
    elif score <= t.strong_bear and a_neg and (b_neg or c_neg):
        return "Vahva laskeva"
    elif score <= t.mild_bear:
        return "Lievästi laskeva"
    else:
        return "Neutraali"


def _pair_bias_label(score: float, percentile: Optional[float]) -> str:
    t = DEFAULT_PAIR_THRESHOLDS
    # Exceptional vaatii joko suoran score-rajan TAI percentilen + minimiscoren
    if score >= t.exceptional_bull_score:
        return "Poikkeuksellinen nouseva"
    elif percentile is not None and percentile >= t.exceptional_bull_percentile and score >= t.mild_bull:
        return "Poikkeuksellinen nouseva"
    elif score >= t.strong_bull:
        return "Vahva nouseva"
    elif score >= t.mild_bull:
        return "Lievästi nouseva"
    elif score <= t.exceptional_bear_score:
        return "Poikkeuksellinen laskeva"
    elif percentile is not None and percentile <= t.exceptional_bear_percentile and score <= t.mild_bear:
        return "Poikkeuksellinen laskeva"
    elif score <= t.strong_bear:
        return "Vahva laskeva"
    elif score <= t.mild_bear:
        return "Lievästi laskeva"
    else:
        return "Neutraali"


# ---------------------------------------------------------------------------
# Pääfunktiot
# ---------------------------------------------------------------------------

def compute_currency_metrics(db: Session) -> pd.DataFrame:
    """
    Laskee kaikki CurrencyMetrics-arvot raakadatasta.
    Palauttaa DataFramen kaikista valuutoista ja viikoista.
    """
    rows = db.query(RawReport).filter(RawReport.is_corrected == False).order_by(RawReport.report_date).all()  # noqa: E712
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "report_date": r.report_date,
        "currency": r.currency,
        "open_interest_total": r.open_interest_total,
        "lev_long": r.lev_long,
        "lev_short": r.lev_short,
        "lev_spreading": r.lev_spreading,
    } for r in rows])

    results = []

    for ccy in CURRENCIES:
        cdf = df[df["currency"] == ccy].copy().sort_values("report_date").reset_index(drop=True)
        if cdf.empty:
            continue

        # Vaihe 1: johdetut perusarvot
        cdf["oi_lf"] = cdf["lev_long"] + cdf["lev_short"] + cdf["lev_spreading"]
        cdf["net_position"] = cdf["lev_long"] - cdf["lev_short"]
        cdf["net_percent_lf"] = cdf["net_position"] / cdf["oi_lf"].replace(0, np.nan)
        cdf["oi_lf_ratio"] = cdf["oi_lf"] / cdf["open_interest_total"].replace(0, np.nan)

        # Vaihe 2: deltat
        cdf["delta_1w"] = cdf["net_percent_lf"].diff(1)
        cdf["delta_4w"] = cdf["net_percent_lf"].diff(4)
        cdf["oi_lf_ratio_delta_4w"] = cdf["oi_lf_ratio"].diff(4)

        # Vaihe 3: z-scoret
        cdf["z_current"] = _rolling_zscore(cdf["net_percent_lf"], ZSCORE_WINDOW)
        cdf["z_delta_1w"] = _rolling_zscore(cdf["delta_1w"], ZSCORE_WINDOW)
        cdf["z_delta_4w"] = _rolling_zscore(cdf["delta_4w"], ZSCORE_WINDOW)
        cdf["z_oi_delta"] = _rolling_zscore(cdf["oi_lf_ratio_delta_4w"], ZSCORE_WINDOW)

        # Vaihe 4: CurrencyScore
        w = DEFAULT_WEIGHTS

        def _score_row(r):
            A = r["z_current"]
            B = r["z_delta_1w"]
            C = r["z_delta_4w"]
            D = r["z_oi_delta"]

            # Fallback-painotus jos C tai D puuttuu
            if pd.isna(C) or pd.isna(D):
                fw = FALLBACK_WEIGHTS_SHORT
                if pd.isna(A) or pd.isna(B):
                    return np.nan
                return fw.w_a * A + fw.w_b * B
            if pd.isna(A) or pd.isna(B):
                return np.nan
            return w.w_a * A + w.w_b * B + w.w_c * C + w.w_d * D

        cdf["currency_score"] = cdf.apply(_score_row, axis=1)

        # Vaihe 5: 52-viikon percentile
        cdf["percentile_52w"] = _percentile_rank(cdf["currency_score"], PERCENTILE_WINDOW)

        # Historia-lippu
        cdf["history_flag"] = "full"
        mask_limited = cdf["currency_score"].notna() & (
            cdf["z_delta_4w"].isna() | cdf["z_oi_delta"].isna()
        )
        cdf.loc[mask_limited, "history_flag"] = "limited"

        # Bias-label ja kommentaari
        def _bias_and_comment(r):
            if pd.isna(r["currency_score"]):
                return pd.Series({"bias_label": "Ei riittävästi dataa", "commentary": None})
            label = _currency_bias_label(
                r["currency_score"],
                r["z_current"],
                r["z_delta_1w"],
                r["z_delta_4w"],
            )
            comment = generate_currency_commentary(
                currency=ccy,
                score=r["currency_score"],
                A=r["z_current"],
                B=r["z_delta_1w"],
                C=r["z_delta_4w"],
                percentile=r["percentile_52w"],
                bias_label=label,
            )
            return pd.Series({"bias_label": label, "commentary": comment})

        cdf[["bias_label", "commentary"]] = cdf.apply(_bias_and_comment, axis=1)

        results.append(cdf)

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)


def compute_pair_metrics(currency_df: pd.DataFrame) -> pd.DataFrame:
    """
    Laskee PairMetrics kaikille valuuttapareille.
    Vaatii compute_currency_metrics()-tuloksen.
    """
    if currency_df.empty:
        return pd.DataFrame()

    # Pivot: rivi = report_date, sarake = currency
    pivot = currency_df.pivot(index="report_date", columns="currency", values="currency_score")

    pair_rows = []
    for base, quote in DISPLAY_PAIRS:
        if base not in pivot.columns or quote not in pivot.columns:
            continue

        pair_name = f"{base}{quote}"
        pair_df = pivot[[base, quote]].dropna().copy()
        pair_df["pair_score"] = pair_df[base] - pair_df[quote]
        pair_df["pair_percentile_52w"] = _percentile_rank(pair_df["pair_score"], PERCENTILE_WINDOW)

        for rd, row in pair_df.iterrows():
            ps = row["pair_score"]
            pct = row["pair_percentile_52w"]
            label = _pair_bias_label(ps, pct if not pd.isna(pct) else None)
            comment = generate_pair_commentary(
                pair=pair_name,
                base=base,
                quote=quote,
                pair_score=ps,
                base_score=row[base],
                quote_score=row[quote],
                percentile=pct,
                bias_label=label,
            )
            pair_rows.append({
                "report_date": rd,
                "pair": pair_name,
                "base_currency": base,
                "quote_currency": quote,
                "base_score": row[base],
                "quote_score": row[quote],
                "pair_score": ps,
                "pair_percentile_52w": pct if not pd.isna(pct) else None,
                "bias_label": label,
                "commentary": comment,
            })

    return pd.DataFrame(pair_rows)


def _save_currency_metrics(db: Session, currency_df: pd.DataFrame) -> int:
    """Tallentaa CurrencyMetrics tietokantaan. Palauttaa tallennettujen rivien määrän."""
    saved = 0
    for _, row in currency_df.iterrows():
        if pd.isna(row.get("currency_score")):
            continue

        existing = (
            db.query(CurrencyMetrics)
            .filter(
                CurrencyMetrics.report_date == row["report_date"],
                CurrencyMetrics.currency == row["currency"],
            )
            .first()
        )

        def _val(v):
            return None if pd.isna(v) else float(v)

        data = {
            "net_position": _val(row.get("net_position")),
            "net_percent_lf": _val(row.get("net_percent_lf")),
            "oi_lf": _val(row.get("oi_lf")),
            "oi_lf_ratio": _val(row.get("oi_lf_ratio")),
            "delta_1w": _val(row.get("delta_1w")),
            "delta_4w": _val(row.get("delta_4w")),
            "oi_lf_ratio_delta_4w": _val(row.get("oi_lf_ratio_delta_4w")),
            "z_current": _val(row.get("z_current")),
            "z_delta_1w": _val(row.get("z_delta_1w")),
            "z_delta_4w": _val(row.get("z_delta_4w")),
            "z_oi_delta": _val(row.get("z_oi_delta")),
            "currency_score": _val(row.get("currency_score")),
            "percentile_52w": _val(row.get("percentile_52w")),
            "bias_label": row.get("bias_label"),
            "commentary": row.get("commentary"),
            "history_flag": row.get("history_flag", "full"),
        }

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            record = CurrencyMetrics(
                report_date=row["report_date"],
                currency=row["currency"],
                **data,
            )
            db.add(record)
        saved += 1

    db.commit()
    return saved


def _save_pair_metrics(db: Session, pair_df: pd.DataFrame) -> int:
    """Tallentaa PairMetrics tietokantaan. Palauttaa tallennettujen rivien määrän."""
    saved = 0
    for _, row in pair_df.iterrows():
        if pd.isna(row.get("pair_score")):
            continue

        existing = (
            db.query(PairMetrics)
            .filter(
                PairMetrics.report_date == row["report_date"],
                PairMetrics.pair == row["pair"],
            )
            .first()
        )

        def _val(v):
            return None if pd.isna(v) else float(v)

        data = {
            "base_currency": row["base_currency"],
            "quote_currency": row["quote_currency"],
            "base_score": _val(row.get("base_score")),
            "quote_score": _val(row.get("quote_score")),
            "pair_score": _val(row.get("pair_score")),
            "pair_percentile_52w": _val(row.get("pair_percentile_52w")),
            "bias_label": row.get("bias_label"),
            "commentary": row.get("commentary"),
        }

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            record = PairMetrics(
                report_date=row["report_date"],
                pair=row["pair"],
                **data,
            )
            db.add(record)
        saved += 1

    db.commit()
    return saved


def recalculate_all(db: Session) -> int:
    """
    Laskee kaiken uudelleen alusta. Käytetään bulk importin jälkeen.
    Palauttaa käsiteltyjen viikkojen määrän.
    """
    logger.info("Aloitetaan täydellinen uudelleenlaskenta...")

    # Tyhjennä vanhat tulokset
    db.query(CurrencyMetrics).delete()
    db.query(PairMetrics).delete()
    db.commit()

    currency_df = compute_currency_metrics(db)
    if currency_df.empty:
        logger.warning("Ei dataa laskentaan.")
        return 0

    c_saved = _save_currency_metrics(db, currency_df)

    pair_df = compute_pair_metrics(currency_df)
    p_saved = _save_pair_metrics(db, pair_df)

    weeks = currency_df["report_date"].nunique()
    logger.info(
        "Laskenta valmis: %d valuuttarivi, %d paririvi, %d viikkoa",
        c_saved, p_saved, weeks,
    )
    return weeks
