from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImportType(str, Enum):
    CASE_INFO = "CASE_INFO"
    CASE_HOME_FILTERED = "CASE_HOME_FILTERED"
    COST_SUMMARY = "COST_SUMMARY"
    COST_DETAIL = "COST_DETAIL"
    DIP_DICT = "DIP_DICT"
    ICD10_DICT = "ICD10_DICT"
    ICD9_DICT = "ICD9_DICT"


class BatchStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ImportBatch(Base):
    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    import_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=BatchStatus.PENDING.value)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
