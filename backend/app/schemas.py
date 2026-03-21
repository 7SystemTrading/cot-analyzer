from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Raw Report
# ---------------------------------------------------------------------------
class RawReportBase(BaseModel):
    report_date: date
    currency: str
    open_interest_total: float
    lev_long: float
    lev_short: float
    lev_spreading: float = 0.0
    contract_name: Optional[str] = None
    source_file: Optional[str] = None


class RawReportOut(RawReportBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Currency Metrics
# ---------------------------------------------------------------------------
class CurrencyMetricsOut(BaseModel):
    report_date: date
    currency: str
    net_position: Optional[float] = None
    net_percent_lf: Optional[float] = None
    oi_lf: Optional[float] = None
    oi_lf_ratio: Optional[float] = None
    delta_1w: Optional[float] = None
    delta_4w: Optional[float] = None
    oi_lf_ratio_delta_4w: Optional[float] = None
    z_current: Optional[float] = None
    z_delta_1w: Optional[float] = None
    z_delta_4w: Optional[float] = None
    z_oi_delta: Optional[float] = None
    currency_score: Optional[float] = None
    percentile_52w: Optional[float] = None
    bias_label: Optional[str] = None
    commentary: Optional[str] = None
    history_flag: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Pair Metrics
# ---------------------------------------------------------------------------
class PairMetricsOut(BaseModel):
    report_date: date
    pair: str
    base_currency: str
    quote_currency: str
    base_score: Optional[float] = None
    quote_score: Optional[float] = None
    pair_score: Optional[float] = None
    pair_percentile_52w: Optional[float] = None
    bias_label: Optional[str] = None
    commentary: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Import Log
# ---------------------------------------------------------------------------
class ImportLogOut(BaseModel):
    id: int
    imported_at: Optional[datetime] = None
    source_type: str
    source_file: Optional[str] = None
    rows_total: int
    rows_inserted: int
    rows_skipped: int
    errors: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DataStatus(BaseModel):
    latest_report_date: Optional[date] = None
    latest_publish_date: Optional[date] = None
    total_weeks: int = 0
    status: str = "no_data"   # "ok" | "delayed" | "no_data"
    message: Optional[str] = None


class DashboardResponse(BaseModel):
    data_status: DataStatus
    top_currencies: List[CurrencyMetricsOut] = []
    bottom_currencies: List[CurrencyMetricsOut] = []
    top_pairs: List[PairMetricsOut] = []
    bottom_pairs: List[PairMetricsOut] = []


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
class ScoreWeightsIn(BaseModel):
    w_a: float = 0.45
    w_b: float = 0.25
    w_c: float = 0.20
    w_d: float = 0.10


class BiasThresholdsIn(BaseModel):
    currency_strong_bull: float = 1.25
    currency_mild_bull: float = 0.50
    currency_mild_bear: float = -0.50
    currency_strong_bear: float = -1.25
    pair_exceptional_bull: float = 2.0
    pair_strong_bull: float = 1.25
    pair_mild_bull: float = 0.50
    pair_mild_bear: float = -0.50
    pair_strong_bear: float = -1.25
    pair_exceptional_bear: float = -2.0


class ConfigOut(BaseModel):
    weights: ScoreWeightsIn
    thresholds: BiasThresholdsIn


# ---------------------------------------------------------------------------
# Import response
# ---------------------------------------------------------------------------
class ImportResult(BaseModel):
    status: str
    rows_total: int
    rows_inserted: int
    rows_skipped: int
    errors: List[str] = []
    message: str


# ---------------------------------------------------------------------------
# Bias Dashboard (erillinen laskentamalli)
# ---------------------------------------------------------------------------
class BiasCurrencyRow(BaseModel):
    currency: str
    net_pct_lf: Optional[float] = None
    delta_1: Optional[float] = None
    delta_2: Optional[float] = None
    delta_3: Optional[float] = None
    delta_4: Optional[float] = None


class BiasPairRow(BaseModel):
    pair: str
    base: str
    quote: str
    strength_index: float
    bias: str
    confirmed: bool = False
    net_pct_lf_base: float
    net_pct_lf_quote: float
    delta_1_base: Optional[float] = None
    delta_1_quote: Optional[float] = None
    delta_2_base: Optional[float] = None
    delta_2_quote: Optional[float] = None
    delta_3_base: Optional[float] = None
    delta_3_quote: Optional[float] = None
    delta_4_base: Optional[float] = None
    delta_4_quote: Optional[float] = None


class BiasDashboardResponse(BaseModel):
    report_date: Optional[date] = None
    threshold: float
    currencies: List[BiasCurrencyRow] = []
    strong_long: List[BiasPairRow] = []
    strong_short: List[BiasPairRow] = []
    neutral_count: int = 0
