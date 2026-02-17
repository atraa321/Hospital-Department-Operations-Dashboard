from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CostDetail(Base):
    __tablename__ = "cost_detail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    patient_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    item_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    item_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dept_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cost_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cost_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    patient_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    import_batch: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

