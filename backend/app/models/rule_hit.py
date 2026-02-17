from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RuleHit(Base):
    __tablename__ = "rule_hit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    diagnosis_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dept_name: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    hit_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
