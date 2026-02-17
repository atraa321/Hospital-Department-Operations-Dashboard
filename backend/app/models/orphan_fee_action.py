from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrphanActionStatus(str, Enum):
    PENDING = "PENDING"
    MARKED = "MARKED"
    REJECTED = "REJECTED"
    SUPPLEMENTED = "SUPPLEMENTED"


class OrphanFeeAction(Base):
    __tablename__ = "orphan_fee_action"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=OrphanActionStatus.PENDING.value)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
