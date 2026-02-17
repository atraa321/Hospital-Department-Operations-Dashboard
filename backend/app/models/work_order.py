from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkOrder(Base):
    __tablename__ = "work_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    hit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_code: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    patient_id: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    dept_name: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False, default="TODO")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
