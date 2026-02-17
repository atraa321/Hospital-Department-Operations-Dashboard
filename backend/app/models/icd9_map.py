from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Icd9Map(Base):
    __tablename__ = "icd9_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    source_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_code: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    target_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    import_batch: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
