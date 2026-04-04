from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class CaseRecordItem(BaseModel):
    patient_id: str
    patient_name: Optional[str]
    gender: Optional[str]
    age: Optional[int]
    doctor_name: Optional[str]
    dept_name: Optional[str]
    admission_date: Optional[date]
    discharge_date: Optional[date]
    los: Optional[int]
    main_diagnosis_code: Optional[str]
    main_diagnosis_name: Optional[str]
    total_cost: float
    drug_cost: float
    material_cost: float
    exam_cost: float
    treatment_cost: float
    surgery_cost: float

    class Config:
        from_attributes = True


class CaseRecordList(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CaseRecordItem]


class DoctorListOut(BaseModel):
    items: list[str]


class DepartmentListOut(BaseModel):
    items: list[str]
