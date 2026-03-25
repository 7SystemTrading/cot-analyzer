"""
COT Dashboard v2 – Pydantic response schemas.
"""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Currency schemas
# ---------------------------------------------------------------------------

class CurrencyBiasItem(BaseModel):
    currency: str
    bias_label: Optional[str]
    currency_score: Optional[float]
    dir_score: Optional[float]
    mom_score: Optional[float]
    strength_score: Optional[float]
    percentile: Optional[float]
    extreme_score: Optional[int]
    reversal_risk: Optional[str]
    reversal_score: Optional[int]
    commercial_opposition: Optional[int]
    nc_net: Optional[float]
    net_change: Optional[float]
    net_pct_oi: Optional[float]
    explanation: Optional[str] = None


class CurrencyHistoryPoint(BaseModel):
    report_date: date
    nc_net: Optional[float]
    comm_net: Optional[float]
    net_change: Optional[float]
    net_pct_oi: Optional[float]
    percentile: Optional[float]
    currency_score: Optional[float]
    bias_label: Optional[str]
    extreme_score: Optional[int]
    reversal_risk: Optional[str]


class CurrencyDetailResponse(BaseModel):
    currency: str
    report_date: Optional[date]
    current: Optional[CurrencyBiasItem]
    history: List[CurrencyHistoryPoint] = []
    available_dates: List[date] = []


class CurrenciesResponse(BaseModel):
    report_date: Optional[date]
    publish_date: Optional[date]
    currencies: List[CurrencyBiasItem] = []


# ---------------------------------------------------------------------------
# Pair schemas
# ---------------------------------------------------------------------------

class PairBiasItem(BaseModel):
    pair: str
    base_currency: str
    quote_currency: str
    pair_score: Optional[float]
    pair_label: Optional[str]
    base_score: Optional[float]
    quote_score: Optional[float]
    conviction: Optional[str]
    conviction_score: Optional[float]
    base_reversal_risk: Optional[str]
    quote_reversal_risk: Optional[str]
    divergence_type: Optional[str]
    divergence_strength: Optional[float]
    explanation: Optional[str] = None


class PairHistoryPoint(BaseModel):
    report_date: date
    pair_score: Optional[float]
    pair_label: Optional[str]
    conviction: Optional[str]
    divergence_type: Optional[str]
    base_nc_net: Optional[float]
    quote_nc_net: Optional[float]


class PairsResponse(BaseModel):
    report_date: Optional[date]
    publish_date: Optional[date]
    pairs: List[PairBiasItem] = []
    available_dates: List[date] = []


class PairDetailResponse(BaseModel):
    pair: str
    report_date: Optional[date]
    current: Optional[PairBiasItem]
    base_detail: Optional[CurrencyBiasItem]
    quote_detail: Optional[CurrencyBiasItem]
    history: List[PairHistoryPoint] = []
    available_dates: List[date] = []


# ---------------------------------------------------------------------------
# Overview schema
# ---------------------------------------------------------------------------

class ExtremeItem(BaseModel):
    currency: str
    bias_label: Optional[str]
    extreme_score: Optional[int]
    percentile: Optional[float]
    reversal_risk: Optional[str]


class EventItem(BaseModel):
    event_type: str        # "bias_shift" | "new_extreme" | "new_divergence"
    subject: str           # currency or pair name
    detail: str            # human-readable description


class OverviewResponse(BaseModel):
    report_date: Optional[date]
    publish_date: Optional[date]
    currencies_ranked: List[CurrencyBiasItem] = []
    top_pairs: List[PairBiasItem] = []
    extremes: List[ExtremeItem] = []
    events: List[EventItem] = []
    available_dates: List[date] = []


# ---------------------------------------------------------------------------
# Data management schemas
# ---------------------------------------------------------------------------

class AppSettingsSchema(BaseModel):
    percentile_window: int = 156
    divergence_window: int = 4
    weight_direction: float = 0.4
    weight_momentum: float = 0.2
    weight_strength: float = 0.4
    extreme_threshold_mild: float = 0.70
    extreme_threshold_major: float = 0.85
    extreme_threshold_historic: float = 0.95


class ImportLogItem(BaseModel):
    id: int
    imported_at: str
    source_type: str
    source_file: Optional[str]
    rows_total: int
    rows_inserted: int
    rows_skipped: int
    status: str
    errors: Optional[str]


class DataStatusResponse(BaseModel):
    latest_report_date: Optional[date]
    total_weeks: int
    total_rows: int
    currencies_covered: List[str]
    recent_logs: List[ImportLogItem] = []
