from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_ADMIN,
    ROLE_DIRECTOR,
    ROLE_FINANCE,
    ROLE_INSURANCE,
    ROLE_MEDICAL,
    ROLE_VIEWER,
    CurrentUser,
    require_roles,
    resolve_dept_scope,
)
from app.db.session import get_db
from app.schemas.records import CaseRecordList, DepartmentListOut, DoctorListOut
from app.services.records_service import (
    get_case_records,
    list_record_departments,
    list_record_doctors,
)

router = APIRouter(prefix="/records", tags=["records"])


@router.get("/cases", response_model=CaseRecordList)
def case_records(
    page: int = 1,
    page_size: int = 20,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    doctor_name: str | None = None,
    disease_name: str | None = None,
    disease_code: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(
            ROLE_ADMIN,
            ROLE_DIRECTOR,
            ROLE_MEDICAL,
            ROLE_INSURANCE,
            ROLE_FINANCE,
            ROLE_VIEWER,
        )
    ),
):
    scoped_dept = resolve_dept_scope(dept_name, current_user)
    masked = current_user.role not in {ROLE_ADMIN}
    return get_case_records(
        db=db,
        page=page,
        page_size=page_size,
        dept_name=scoped_dept,
        date_from=date_from,
        date_to=date_to,
        doctor_name=doctor_name,
        disease_name=disease_name,
        disease_code=disease_code,
        masked=masked,
    )


@router.get("/departments", response_model=DepartmentListOut)
def record_departments(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(
            ROLE_ADMIN,
            ROLE_DIRECTOR,
            ROLE_MEDICAL,
            ROLE_INSURANCE,
            ROLE_FINANCE,
            ROLE_VIEWER,
        )
    ),
):
    dept_items = list_record_departments(db)
    if current_user.role == ROLE_ADMIN:
        return dept_items
    if current_user.dept_name:
        return {"items": [current_user.dept_name]}
    return {"items": []}


@router.get("/doctors", response_model=DoctorListOut)
def record_doctors(
    dept_name: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(
            ROLE_ADMIN,
            ROLE_DIRECTOR,
            ROLE_MEDICAL,
            ROLE_INSURANCE,
            ROLE_FINANCE,
            ROLE_VIEWER,
        )
    ),
):
    scoped_dept = resolve_dept_scope(dept_name, current_user)
    return list_record_doctors(db, dept_name=scoped_dept)
