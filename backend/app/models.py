"""
COT Dashboard v2 – Database models
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class CotRaw(Base):
    """Raw CFTC Legacy COT data – one row per week per currency."""
    __tablename__ = "cot_raw"
    __table_args__ = (
        UniqueConstraint("report_date", "currency", name="uq_cot_raw"),
    )

    id = Column(Integer, primary_key=True, index=True)
    report_date  = Column(Date, nullable=False, index=True)
    currency     = Column(String(8), nullable=False, index=True)
    contract_name = Column(String(200), nullable=True)

    # Non-commercial (speculators)
    nc_long  = Column(Float, nullable=False)
    nc_short = Column(Float, nullable=False)

    # Commercial (hedgers)
    comm_long  = Column(Float, nullable=False)
    comm_short = Column(Float, nullable=False)

    # Non-reportable (retail)
    nr_long  = Column(Float, nullable=False)
    nr_short = Column(Float, nullable=False)

    open_interest = Column(Float, nullable=False)

    source_file = Column(String(500), nullable=True)
    created_at  = Column(DateTime, server_default=func.now())


class CotDerived(Base):
    """Computed metrics per currency per week (spec sections 20.1–20.12)."""
    __tablename__ = "cot_derived"
    __table_args__ = (
        UniqueConstraint("report_date", "currency", name="uq_cot_derived"),
    )

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, nullable=False, index=True)
    currency    = Column(String(8), nullable=False, index=True)

    # Derived nets (spec 20.1)
    nc_net   = Column(Float, nullable=True)
    comm_net = Column(Float, nullable=True)
    nr_net   = Column(Float, nullable=True)

    # Weekly changes (spec 20.2)
    net_change = Column(Float, nullable=True)   # nc_net change week-over-week
    oi_change  = Column(Float, nullable=True)

    # Normalization (spec 20.3)
    net_pct_oi = Column(Float, nullable=True)   # nc_net / open_interest

    # Statistical (spec 20.4–20.5)
    percentile = Column(Float, nullable=True)   # 0–1 over PERCENTILE_WINDOW
    z_score    = Column(Float, nullable=True)

    # Component scores (spec 20.7–20.9)
    dir_score      = Column(Float, nullable=True)   # sign(nc_net)
    mom_score      = Column(Float, nullable=True)   # sign(net_change)
    strength_score = Column(Float, nullable=True)   # percentile * dir_score

    # Composite currency score [-2, +2] (spec 20.10)
    currency_score = Column(Float, nullable=True)
    bias_label     = Column(String(50), nullable=True)

    # Extreme detection (spec 20.6)
    extreme_score = Column(Integer, nullable=True)   # 0/1/2/3

    # Reversal risk (spec 20.12)
    commercial_opposition = Column(Integer, nullable=True)  # 0/1
    reversal_score        = Column(Integer, nullable=True)  # 0–4
    reversal_risk         = Column(String(10), nullable=True)  # Low/Medium/High

    created_at = Column(DateTime, server_default=func.now())


class CotPairs(Base):
    """Pair-level metrics per week (spec sections 20.13–20.16)."""
    __tablename__ = "cot_pairs"
    __table_args__ = (
        UniqueConstraint("report_date", "pair", name="uq_cot_pairs"),
    )

    id = Column(Integer, primary_key=True, index=True)
    report_date    = Column(Date, nullable=False, index=True)
    pair           = Column(String(8), nullable=False, index=True)
    base_currency  = Column(String(8), nullable=False)
    quote_currency = Column(String(8), nullable=False)

    base_score  = Column(Float, nullable=True)
    quote_score = Column(Float, nullable=True)

    # Pair score [-4, +4] (spec 20.13)
    pair_score  = Column(Float, nullable=True)
    pair_label  = Column(String(50), nullable=True)

    # Conviction (spec 20.15)
    conviction_score = Column(Float, nullable=True)
    conviction       = Column(String(10), nullable=True)  # Low/Medium/High

    # Divergence (spec 20.16)
    divergence_type     = Column(String(20), nullable=True)   # Bullish/Bearish/None
    divergence_strength = Column(Float, nullable=True)
    divergence_active   = Column(String(5), nullable=True)    # true/false/null

    created_at = Column(DateTime, server_default=func.now())


class PriceData(Base):
    """Daily OHLC price cache (yfinance) for divergence calculations."""
    __tablename__ = "price_data"
    __table_args__ = (
        UniqueConstraint("pair", "date", name="uq_price_data"),
    )

    id    = Column(Integer, primary_key=True, index=True)
    pair  = Column(String(8), nullable=False, index=True)
    date  = Column(Date, nullable=False, index=True)
    open  = Column(Float, nullable=False)
    high  = Column(Float, nullable=False)
    low   = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class AppSettings(Base):
    """User-configurable calculation settings (§16). Single-row table."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    percentile_window   = Column(Integer,  default=156)   # weeks
    divergence_window   = Column(Integer,  default=4)     # weeks
    weight_direction    = Column(Float,    default=0.4)
    weight_momentum     = Column(Float,    default=0.2)
    weight_strength     = Column(Float,    default=0.4)
    extreme_threshold_mild     = Column(Float, default=0.70)
    extreme_threshold_major    = Column(Float, default=0.85)
    extreme_threshold_historic = Column(Float, default=0.95)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ImportLog(Base):
    """Data import operation log."""
    __tablename__ = "import_log"

    id          = Column(Integer, primary_key=True, index=True)
    imported_at = Column(DateTime, server_default=func.now())
    source_type = Column(String(20), nullable=False)   # "auto" | "manual" | "history"
    source_file = Column(String(500), nullable=True)
    rows_total    = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    rows_skipped  = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    status = Column(String(20), default="ok")          # "ok" | "partial" | "failed"
