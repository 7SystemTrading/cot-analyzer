"""
Sovelluksen konfiguraatio – kaikki painot, kynnysarvot ja sopimustunnisteet.
Nämä voidaan päivittää API:n kautta ilman koodimuutoksia.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Valuuttasopimusten tunnisteet CFTC-datassa
# ---------------------------------------------------------------------------
CURRENCY_CONTRACTS: Dict[str, str] = {
    "EUR": "EURO FX",
    "GBP": "BRITISH POUND",
    "JPY": "JAPANESE YEN",
    "CAD": "CANADIAN DOLLAR",
    "CHF": "SWISS FRANC",
    "AUD": "AUSTRALIAN DOLLAR",
    "NZD": "NZ DOLLAR",
    "USD": "USD INDEX",
}

CURRENCIES: List[str] = list(CURRENCY_CONTRACTS.keys())

# USD-major parit esitetään ensin, sitten crossit
DISPLAY_PAIRS: List[Tuple[str, str]] = [
    ("EUR", "USD"), ("GBP", "USD"), ("USD", "JPY"),
    ("USD", "CAD"), ("USD", "CHF"), ("AUD", "USD"), ("NZD", "USD"),
    ("EUR", "GBP"), ("EUR", "JPY"), ("EUR", "CAD"), ("EUR", "CHF"),
    ("EUR", "AUD"), ("EUR", "NZD"),
    ("GBP", "JPY"), ("GBP", "CAD"), ("GBP", "CHF"), ("GBP", "AUD"), ("GBP", "NZD"),
    ("AUD", "JPY"), ("AUD", "CAD"), ("AUD", "CHF"), ("AUD", "NZD"),
    ("NZD", "JPY"), ("NZD", "CAD"), ("NZD", "CHF"),
    ("CAD", "JPY"), ("CAD", "CHF"),
    ("CHF", "JPY"),
]


# ---------------------------------------------------------------------------
# Laskentapainot (CurrencyScore = w_A*A + w_B*B + w_C*C + w_D*D)
# ---------------------------------------------------------------------------
@dataclass
class ScoreWeights:
    w_a: float = 0.45   # Current Positioning Extremity
    w_b: float = 0.25   # Short-Term Momentum (1vk)
    w_c: float = 0.20   # Medium-Term Momentum (4vk)
    w_d: float = 0.10   # Participation Confirmation


DEFAULT_WEIGHTS = ScoreWeights()

# Fallback-painot kun historiaa < 4 viikkoa (C ja D pois)
FALLBACK_WEIGHTS_SHORT = ScoreWeights(w_a=0.64, w_b=0.36, w_c=0.0, w_d=0.0)


# ---------------------------------------------------------------------------
# Z-score- ja percentile-ikkunat
# ---------------------------------------------------------------------------
ZSCORE_WINDOW: int = 26      # viikkoa
PERCENTILE_WINDOW: int = 52  # viikkoa
MIN_HISTORY_WEEKS: int = 26  # vähimmäishistoria laskentaan


# ---------------------------------------------------------------------------
# Currency Bias -kynnysarvot
# ---------------------------------------------------------------------------
@dataclass
class CurrencyBiasThresholds:
    strong_bull: float = 1.25
    mild_bull: float = 0.50
    mild_bear: float = -0.50
    strong_bear: float = -1.25


DEFAULT_CURRENCY_THRESHOLDS = CurrencyBiasThresholds()


# ---------------------------------------------------------------------------
# Pair Bias -kynnysarvot
# ---------------------------------------------------------------------------
@dataclass
class PairBiasThresholds:
    exceptional_bull_score: float = 2.0
    exceptional_bull_percentile: float = 90.0
    strong_bull: float = 1.25
    mild_bull: float = 0.50
    mild_bear: float = -0.50
    strong_bear: float = -1.25
    exceptional_bear_score: float = -2.0
    exceptional_bear_percentile: float = 10.0


DEFAULT_PAIR_THRESHOLDS = PairBiasThresholds()


# ---------------------------------------------------------------------------
# CFTC-datan URL-mallit
# ---------------------------------------------------------------------------
CFTC_HISTORY_URL_TEMPLATE = (
    "https://www.cftc.gov/files/dea/history/fut_fin_xls_{year}.zip"
)
CFTC_CURRENT_URL = (
    "https://publicreporting.cftc.gov/api/views/gpe5-46if/rows.csv"
)
CFTC_FIRST_YEAR = 2010

# CSV-kolumnien nimet CFTC-datassa
CFTC_COLUMNS = {
    "date": "Report_Date_as_MM_DD_YYYY",
    "market": "Market_and_Exchange_Names",
    "oi_total": "Open_Interest_All",
    "lev_long": "Lev_Money_Positions_Long_All",
    "lev_short": "Lev_Money_Positions_Short_All",
    "lev_spread": "Lev_Money_Positions_Spread_All",
}
