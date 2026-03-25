"""
COT Dashboard v2 – Rule-based explanation engine (English).
Implements spec sections 10–11.
Deterministic template logic — no LLM.
"""
from typing import Optional


def currency_explanation(
    symbol: str,
    bias_label: str,
    dir_score: Optional[float],
    mom_score: Optional[float],
    percentile: Optional[float],
    reversal_risk: Optional[str],
    commercial_opposition: Optional[int],
    extreme_score: Optional[int],
) -> str:
    """
    Generate a plain-English explanation for a single currency's COT position.
    Spec section 10 + example 11.1.
    """
    if bias_label is None:
        return f"{symbol}: Insufficient data to determine bias."

    parts = []

    # Opening bias statement
    parts.append(f"{symbol} is {bias_label.lower()}.")

    # Direction and momentum (spec 10.1, 10.4)
    if dir_score is not None and mom_score is not None:
        if dir_score > 0 and mom_score > 0:
            parts.append(
                "Speculative positioning is net long and increased this week, "
                "indicating strengthening bullish sentiment."
            )
        elif dir_score > 0 and mom_score < 0:
            parts.append(
                "Speculative positioning is net long but decreased this week, "
                "suggesting weakening bullish momentum."
            )
        elif dir_score < 0 and mom_score < 0:
            parts.append(
                "Speculative positioning is net short and decreased further this week, "
                "indicating strengthening bearish sentiment."
            )
        elif dir_score < 0 and mom_score > 0:
            parts.append(
                "Speculative positioning is net short but recovered this week, "
                "suggesting weakening bearish momentum."
            )
        elif mom_score == 0:
            direction = "long" if dir_score > 0 else "short"
            parts.append(
                f"Speculative positioning is net {direction} with no change this week."
            )

    # Extreme context (spec 10.2)
    if extreme_score is not None and extreme_score > 0:
        pct_str = f"{round(percentile * 100)}th" if percentile is not None else "high"
        if extreme_score == 3:
            parts.append(
                f"Positioning is at a historical extreme ({pct_str} percentile), "
                "indicating potential exhaustion and elevated reversal risk."
            )
        elif extreme_score == 2:
            parts.append(
                f"Positioning is at a major extreme ({pct_str} percentile), "
                "raising the possibility of a sentiment reversal."
            )
        elif extreme_score == 1:
            parts.append(
                f"Positioning shows mild crowding ({pct_str} percentile)."
            )

    # Commercial opposition (spec 10.3)
    if commercial_opposition == 1:
        parts.append(
            "Commercials (hedgers) are positioned opposite to speculators, "
            "which may indicate overextension in the speculative position."
        )

    # Reversal risk summary
    if reversal_risk == "High":
        parts.append("Overall reversal risk is high.")
    elif reversal_risk == "Medium":
        parts.append("Overall reversal risk is moderate.")

    return " ".join(parts)


def pair_explanation(
    pair: str,
    pair_label: str,
    base: str,
    quote: str,
    base_bias: str,
    quote_bias: str,
    conviction: str,
    base_reversal: Optional[str],
    quote_reversal: Optional[str],
    divergence_type: Optional[str],
    divergence_strength: Optional[float],
) -> str:
    """
    Generate a plain-English explanation for a currency pair.
    Spec section 10.5 + example 11.2.
    """
    if pair_label is None:
        return f"{pair}: Insufficient data."

    parts = []

    # Opening pair bias (spec 11.2)
    direction = "bullish" if "Bullish" in pair_label else "bearish" if "Bearish" in pair_label else "neutral"
    parts.append(f"{pair} is {direction}.")

    # Relative strength explanation (spec 10.5)
    if direction != "neutral":
        stronger, weaker = (base, quote) if "Bullish" in pair_label else (quote, base)
        parts.append(
            f"This reflects stronger COT positioning in {stronger} relative to {weaker} "
            f"({base} is {base_bias.lower()}, {quote} is {quote_bias.lower()})."
        )

    # Conviction
    parts.append(f"Signal conviction is {conviction.lower()}.")

    # Reversal risk penalty context
    high_rr = []
    if base_reversal == "High":
        high_rr.append(base)
    if quote_reversal == "High":
        high_rr.append(quote)
    if high_rr:
        parts.append(
            f"Note: {' and '.join(high_rr)} shows elevated reversal risk, "
            "which reduces conviction."
        )

    # Divergence (spec 10 → divergence context)
    if divergence_type == "Bullish":
        strength_desc = "strong" if divergence_strength and divergence_strength > 0.5 else "moderate"
        parts.append(
            f"A {strength_desc} bullish divergence is detected: price is trending lower "
            "while COT positioning is improving — a potential bullish reversal signal."
        )
    elif divergence_type == "Bearish":
        strength_desc = "strong" if divergence_strength and divergence_strength > 0.5 else "moderate"
        parts.append(
            f"A {strength_desc} bearish divergence is detected: price is trending higher "
            "while COT positioning is deteriorating — a potential bearish reversal signal."
        )

    return " ".join(parts)
