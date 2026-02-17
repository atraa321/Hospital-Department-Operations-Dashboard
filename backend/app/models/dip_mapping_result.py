from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DipMappingResult(Base):
    __tablename__ = "dip_mapping_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    diagnosis_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    surgery_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mapped_diag_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mapped_surgery_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dip_code: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    dip_weight_score: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNMAPPED")
    fail_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="AUTO")
    import_batch: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
