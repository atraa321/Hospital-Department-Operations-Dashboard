from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CaseInfo(Base):
    __tablename__ = "case_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    patient_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dept_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dept_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    admission_dept: Mapped[str | None] = mapped_column(String(100), nullable=True)
    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discharge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    los: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diagnosis_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    main_diagnosis_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    main_diagnosis_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    icd_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    icd3_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    surgery_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    surgery_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    total_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    drug_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    herb_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    material_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    exam_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    treatment_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    surgery_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    nursing_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    service_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    other_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    import_batch: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
