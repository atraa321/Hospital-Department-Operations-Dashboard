from __future__ import annotations

from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.case_info import CaseInfo


def _base_conditions(
    dept_name: str | None,
    date_from: date | None,
    date_to: date | None,
    doctor_name: str | None,
    disease_name: str | None,
    disease_code: str | None,
):
    conditions = []
    if dept_name:
        conditions.append(CaseInfo.dept_name == dept_name)
    if date_from:
        conditions.append(CaseInfo.discharge_date >= date_from)
    if date_to:
        conditions.append(CaseInfo.discharge_date <= date_to)
    if doctor_name:
        conditions.append(CaseInfo.doctor_name.ilike(f"%{doctor_name}%"))
    if disease_name:
        conditions.append(CaseInfo.main_diagnosis_name.ilike(f"%{disease_name}%"))
    if disease_code:
        conditions.append(CaseInfo.main_diagnosis_code.ilike(f"%{disease_code}%"))
    return conditions


def get_case_records(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    doctor_name: str | None = None,
    disease_name: str | None = None,
    disease_code: str | None = None,
    masked: bool = True,
) -> dict:
    conditions = _base_conditions(dept_name, date_from, date_to, doctor_name, disease_name, disease_code)

    base_stmt = select(CaseInfo)
    if conditions:
        base_stmt = base_stmt.where(and_(*conditions))

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.scalar(count_stmt) or 0

    data_stmt = (
        base_stmt
        .order_by(CaseInfo.discharge_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(data_stmt).scalars().all()

    def _mask_name(name: str | None) -> str | None:
        if not masked or not name:
            return name
        return name[0] + "**" if len(name) >= 1 else "**"

    def _mask_patient_id(pid: str) -> str:
        if not masked or not pid:
            return pid
        return pid[:4] + "***" if len(pid) > 4 else pid[:2] + "***"

    items = [
        {
            "patient_id": _mask_patient_id(row.patient_id),
            "patient_name": _mask_name(row.patient_name),
            "gender": row.gender,
            "age": row.age,
            "doctor_name": row.doctor_name,
            "dept_name": row.dept_name,
            "admission_date": row.admission_date,
            "discharge_date": row.discharge_date,
            "los": row.los,
            "main_diagnosis_code": row.main_diagnosis_code,
            "main_diagnosis_name": row.main_diagnosis_name,
            "total_cost": float(row.total_cost or 0),
            "drug_cost": float(row.drug_cost or 0),
            "material_cost": float(row.material_cost or 0),
            "exam_cost": float(row.exam_cost or 0),
            "treatment_cost": float(row.treatment_cost or 0),
            "surgery_cost": float(row.surgery_cost or 0),
        }
        for row in rows
    ]

    return {"total": total, "page": page, "page_size": page_size, "items": items}


def list_record_departments(db: Session) -> dict:
    stmt = (
        select(CaseInfo.dept_name)
        .where(CaseInfo.dept_name.is_not(None))
        .group_by(CaseInfo.dept_name)
        .order_by(CaseInfo.dept_name.asc())
    )
    rows = db.execute(stmt).scalars().all()
    return {"items": list(rows)}


def list_record_doctors(db: Session, dept_name: str | None = None) -> dict:
    stmt = select(CaseInfo.doctor_name).where(CaseInfo.doctor_name.is_not(None))
    if dept_name:
        stmt = stmt.where(CaseInfo.dept_name == dept_name)
    stmt = stmt.group_by(CaseInfo.doctor_name).order_by(CaseInfo.doctor_name.asc())
    rows = db.execute(stmt).scalars().all()
    return {"items": list(rows)}
