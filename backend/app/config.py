"""
COT Dashboard v2 – Configuration
Based on spec: cot_dashboard_spec_v_2_dev_ready.md
"""
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------

# Financial Futures COT – Leveraged Funds = speculators, Dealer = hedgers
CFTC_BASE_URL = "https://www.cftc.gov/files/dea/history/deahistfo{year}.zip"

# ---------------------------------------------------------------------------
# Currency contracts in Legacy COT "Market_and_Exchange_Names" column
# Uses startswith matching to handle minor variations
# ---------------------------------------------------------------------------
# Exact prefixes — include the " - " separator to avoid false matches on cross-rate contracts
# e.g. "EURO FX - " prevents matching "EURO FX/BRITISH POUND XRATE"
CURRENCY_CONTRACTS: dict[str, str] = {
    "EUR": "EURO FX - ",
    "GBP": "BRITISH POUND - ",
    "JPY": "JAPANESE YEN - ",
    "CAD": "CANADIAN DOLLAR - ",
    "CHF": "SWISS FRANC - ",
    "AUD": "AUSTRALIAN DOLLAR - ",
    "NZD": "NZ DOLLAR - ",
    "USD": "USD INDEX - ",
}

CURRENCY_HIERARCHY = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY"]

# 28 standard forex pairs
DISPLAY_PAIRS: list[tuple[str, str]] = [
    ("EUR", "GBP"), ("EUR", "AUD"), ("EUR", "NZD"), ("EUR", "USD"),
    ("EUR", "CAD"), ("EUR", "CHF"), ("EUR", "JPY"),
    ("GBP", "AUD"), ("GBP", "NZD"), ("GBP", "USD"),
    ("GBP", "CAD"), ("GBP", "CHF"), ("GBP", "JPY"),
    ("AUD", "NZD"), ("AUD", "USD"), ("AUD", "CAD"),
    ("AUD", "CHF"), ("AUD", "JPY"),
    ("NZD", "USD"), ("NZD", "CAD"), ("NZD", "CHF"), ("NZD", "JPY"),
    ("USD", "CAD"), ("USD", "CHF"), ("USD", "JPY"),
    ("CAD", "CHF"), ("CAD", "JPY"),
    ("CHF", "JPY"),
]

# ---------------------------------------------------------------------------
# Financial Futures COT column names
# ---------------------------------------------------------------------------
COT_COLUMNS = {
    "market":        "Market and Exchange Names",
    "date":          "As of Date in Form YYYY-MM-DD",
    "open_interest": "Open Interest (All)",
    # Non-commercials = speculators (large speculators, hedge funds)
    "nc_long":       "Noncommercial Positions-Long (All)",
    "nc_short":      "Noncommercial Positions-Short (All)",
    # Commercials = hedgers (corporations hedging currency exposure)
    "comm_long":     "Commercial Positions-Long (All)",
    "comm_short":    "Commercial Positions-Short (All)",
    # Non-reportable (retail / small traders)
    "nr_long":       "Nonreportable Positions-Long (All)",
    "nr_short":      "Nonreportable Positions-Short (All)",
}

# ---------------------------------------------------------------------------
# Scoring parameters (spec section 20)
# ---------------------------------------------------------------------------

# Percentile calculation window (weeks)
PERCENTILE_WINDOW = 156  # 3 years default

# Currency score weights (spec 20.10)
@dataclass
class ScoreWeights:
    direction: float = 0.4
    momentum:  float = 0.2
    strength:  float = 0.4

SCORE_WEIGHTS = ScoreWeights()

# Extreme score thresholds (spec 20.6)
# List of (min_percentile, score) in descending order
EXTREME_THRESHOLDS = [
    (0.95, 3),
    (0.85, 2),
    (0.70, 1),
    (0.00, 0),
]

# Reversal risk classification (spec 20.12)
# List of (min_reversal_score, label)
REVERSAL_RISK_LEVELS = [
    (3, "High"),
    (2, "Medium"),
    (0, "Low"),
]

# Currency bias classification (spec 20.11)
# List of (min_score, label); last entry has min_score=None (catch-all)
CURRENCY_BIAS_LEVELS = [
    ( 1.5, "Strong Bullish"),
    ( 0.5, "Bullish"),
    (-0.5, "Neutral"),
    (-1.5, "Bearish"),
    (None, "Strong Bearish"),
]

# Pair bias classification (spec 20.14)
PAIR_BIAS_LEVELS = [
    ( 2.0, "Strong Bullish"),
    ( 1.0, "Bullish"),
    ( 0.0, "Neutral"),
    (-1.0, "Bearish"),
    (None, "Strong Bearish"),
]

# Conviction classification (spec 20.15)
# List of (min_score, label)
CONVICTION_LEVELS = [
    (2, "High"),
    (1, "Medium"),
    (0, "Low"),
]

# Divergence detection window (weeks, spec 20.16)
DIVERGENCE_WINDOW = 4
