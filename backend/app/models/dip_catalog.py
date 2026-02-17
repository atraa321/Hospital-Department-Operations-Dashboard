from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DipCatalog(Base):
    __tablename__ = "dip_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    dip_code: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_score: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    dip_avg_fee: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    avg_ipt_days: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    import_batch: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
