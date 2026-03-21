"""
Suomenkielinen automaattinen tekstigeneraattori valuutoille ja valuuttapareille.
Template-pohjainen – ei LLM:ää, deterministinen.
"""
from typing import Optional


# ---------------------------------------------------------------------------
# Apusanat
# ---------------------------------------------------------------------------

def _score_adj(score: float) -> str:
    """Pistemäärään perustuva adjektiivi."""
    if score >= 1.5:
        return "erittäin vahva"
    elif score >= 0.75:
        return "vahva"
    elif score >= 0.25:
        return "lievästi vahvistuva"
    elif score >= -0.25:
        return "neutraali"
    elif score >= -0.75:
        return "lievästi heikkeneva"
    elif score >= -1.5:
        return "heikko"
    else:
        return "erittäin heikko"


def _momentum_desc(B: Optional[float], C: Optional[float]) -> str:
    """Kuvaa lyhyen ja keskipitkän aikavälin momentumin."""
    if B is None and C is None:
        return "momentumia ei voida arvioida"

    if B is None:
        b_txt = "lyhyen aikavälin muutos ei saatavilla"
    elif B > 0.5:
        b_txt = "viikkomuutos on selvästi positiivinen"
    elif B > 0:
        b_txt = "viikkomuutos on lievästi positiivinen"
    elif B < -0.5:
        b_txt = "viikkomuutos on selvästi negatiivinen"
    else:
        b_txt = "viikkomuutos on lievästi negatiivinen"

    if C is None:
        return b_txt
    elif C > 0.5:
        c_txt = "neljän viikon trendi on nouseva"
    elif C > 0:
        c_txt = "neljän viikon trendi on lievästi nouseva"
    elif C < -0.5:
        c_txt = "neljän viikon trendi on laskeva"
    else:
        c_txt = "neljän viikon trendi on lievästi laskeva"

    return f"{b_txt}, ja {c_txt}"


def _positioning_direction(A: Optional[float]) -> str:
    """Kuvaa positioning-tason suhteessa historialliseen normiin."""
    if A is None:
        return "historiallista vertailua ei saatavilla"
    elif A > 1.0:
        return "selvästi normaalia korkeampi"
    elif A > 0.3:
        return "lievästi normaalia korkeampi"
    elif A < -1.0:
        return "selvästi normaalia matalampi"
    elif A < -0.3:
        return "lievästi normaalia matalampi"
    else:
        return "lähellä historiallista normaalia"


def _exhaustion_warning(score: float, percentile: Optional[float]) -> str:
    """Varoitus jos positioning on äärimmäinen."""
    if percentile is None:
        return ""
    if percentile >= 90 and score > 0:
        return (
            " Huomio: positioning on lähellä historiallista ääriarvoa, "
            "mikä voi ennakoida kasvavaa reversal-riskiä."
        )
    if percentile <= 10 and score < 0:
        return (
            " Huomio: negatiivinen positioning on historiallisesti äärimmäinen, "
            "mikä voi ennakoida kasvavaa reversal-riskiä."
        )
    return ""


def _percentile_desc(percentile: Optional[float]) -> str:
    if percentile is None:
        return "historiallinen vertailu ei saatavilla"
    elif percentile >= 90:
        return f"{percentile:.0f}. persentiilillä (poikkeuksellisen korkea)"
    elif percentile >= 75:
        return f"{percentile:.0f}. persentiilillä (selvästi korkea)"
    elif percentile >= 25:
        return f"{percentile:.0f}. persentiilillä (normaali vaihteluväli)"
    elif percentile >= 10:
        return f"{percentile:.0f}. persentiilillä (selvästi matala)"
    else:
        return f"{percentile:.0f}. persentiilillä (poikkeuksellisen matala)"


# ---------------------------------------------------------------------------
# Valuuttakuvaus
# ---------------------------------------------------------------------------

def generate_currency_commentary(
    currency: str,
    score: float,
    A: Optional[float],
    B: Optional[float],
    C: Optional[float],
    percentile: Optional[float],
    bias_label: str,
) -> str:
    adj = _score_adj(score)
    pos_dir = _positioning_direction(A)
    momentum = _momentum_desc(B, C)
    pct_desc = _percentile_desc(percentile)
    warning = _exhaustion_warning(score, percentile)

    return (
        f"{currency} on tällä viikolla {adj} (score: {score:+.2f}, {pct_desc}). "
        f"Nykyinen nettopositio on {pos_dir} suhteessa historialliseen normiin. "
        f"{momentum.capitalize()}.{warning}"
    ).strip()


# ---------------------------------------------------------------------------
# Parikuvaus
# ---------------------------------------------------------------------------

def _pair_context(pair_score: float, percentile: Optional[float]) -> str:
    """Lisäkonteksti parin tilanteesta."""
    if percentile is not None and percentile >= 90:
        return (
            "Parin suhteellinen positioning on lähellä historiallista ääriarvoa, "
            "mikä tukee rakennetta mutta lisää myös reversal-riskiä."
        )
    if percentile is not None and percentile <= 10:
        return (
            "Parin suhteellinen positioning on historiallisesti äärimmäisen heikko, "
            "mikä voi ennakoida korjausliikettä."
        )
    if abs(pair_score) < 0.5:
        return "Parin välillä ei ole tällä hetkellä merkittävää suhteellista etua."
    return ""


def generate_pair_commentary(
    pair: str,
    base: str,
    quote: str,
    pair_score: float,
    base_score: float,
    quote_score: float,
    percentile: Optional[float],
    bias_label: str,
) -> str:
    base_adj = _score_adj(base_score)
    quote_adj = _score_adj(quote_score)
    pct_desc = _percentile_desc(percentile)
    context = _pair_context(pair_score, percentile)

    direction = "bullish" if pair_score > 0 else "bearish" if pair_score < 0 else "neutraali"

    text = (
        f"{pair} muodostaa tällä viikolla {bias_label.lower()}-biasin "
        f"(pair score: {pair_score:+.2f}, {pct_desc}). "
        f"{base} on {base_adj}, kun taas {quote} on {quote_adj}."
    )
    if context:
        text += f" {context}"

    return text.strip()
