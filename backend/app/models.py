from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    Boolean, Text, UniqueConstraint
)
from sqlalchemy.sql import func
from app.database import Base


class RawReport(Base):
    """CFTC:n raakadata – yksi rivi per viikko per valuutta."""
    __tablename__ = "raw_reports"
    __table_args__ = (
        UniqueConstraint("report_date", "currency", name="uq_raw_report"),
    )

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, nullable=False, index=True)
    publish_date = Column(Date, nullable=True)
    currency = Column(String(8), nullable=False, index=True)
    contract_name = Column(String(200), nullable=True)
    open_interest_total = Column(Float, nullable=False)
    lev_long = Column(Float, nullable=False)
    lev_short = Column(Float, nullable=False)
    lev_spreading = Column(Float, nullable=False, default=0.0)
    source_file = Column(String(500), nullable=True)
    is_corrected = Column(Boolean, default=False)
    correction_note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class CurrencyMetrics(Base):
    """Lasketut valuuttakohtaiset metriikat per viikko."""
    __tablename__ = "currency_metrics"
    __table_args__ = (
        UniqueConstraint("report_date", "currency", name="uq_currency_metrics"),
    )

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, nullable=False, index=True)
    currency = Column(String(8), nullable=False, index=True)

    # Johdetut perusarvot
    net_position = Column(Float, nullable=True)
    net_percent_lf = Column(Float, nullable=True)
    oi_lf = Column(Float, nullable=True)
    oi_lf_ratio = Column(Float, nullable=True)

    # Deltat
    delta_1w = Column(Float, nullable=True)
    delta_4w = Column(Float, nullable=True)
    oi_lf_ratio_delta_4w = Column(Float, nullable=True)

    # Z-score-komponentit
    z_current = Column(Float, nullable=True)     # A
    z_delta_1w = Column(Float, nullable=True)    # B
    z_delta_4w = Column(Float, nullable=True)    # C
    z_oi_delta = Column(Float, nullable=True)    # D

    # Lopulliset pisteet
    currency_score = Column(Float, nullable=True)
    percentile_52w = Column(Float, nullable=True)

    # Tulkinta
    bias_label = Column(String(50), nullable=True)
    commentary = Column(Text, nullable=True)
    history_flag = Column(String(20), default="full")  # "full" | "limited"

    created_at = Column(DateTime, server_default=func.now())


class PairMetrics(Base):
    """Lasketut valuuttaparikohtaiset metriikat per viikko."""
    __tablename__ = "pair_metrics"
    __table_args__ = (
        UniqueConstraint("report_date", "pair", name="uq_pair_metrics"),
    )

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, nullable=False, index=True)
    pair = Column(String(8), nullable=False, index=True)
    base_currency = Column(String(8), nullable=False)
    quote_currency = Column(String(8), nullable=False)

    base_score = Column(Float, nullable=True)
    quote_score = Column(Float, nullable=True)
    pair_score = Column(Float, nullable=True)
    pair_percentile_52w = Column(Float, nullable=True)

    bias_label = Column(String(50), nullable=True)
    commentary = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


class ImportLog(Base):
    """Import-operaatioiden lokitiedot."""
    __tablename__ = "import_log"

    id = Column(Integer, primary_key=True, index=True)
    imported_at = Column(DateTime, server_default=func.now())
    source_type = Column(String(20), nullable=False)   # "auto" | "manual" | "history"
    source_file = Column(String(500), nullable=True)
    rows_total = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    status = Column(String(20), default="ok")          # "ok" | "partial" | "failed"
