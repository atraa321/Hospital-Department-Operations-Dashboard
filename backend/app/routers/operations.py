from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
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
from app.schemas.operations import DepartmentDetailOut, DepartmentRankingItemOut, OperationsOverviewOut
from app.services.operations_service import (
    get_department_operation_detail,
    get_operations_overview,
    list_department_rankings,
)

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/overview", response_model=OperationsOverviewOut)
def operations_overview(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 12,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
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
    return get_operations_overview(db=db, date_from=date_from, date_to=date_to, limit=limit)


@router.get("/rankings", response_model=list[DepartmentRankingItemOut])
def operations_rankings(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
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
    result = list_department_rankings(db=db, date_from=date_from, date_to=date_to, limit=limit)
    return result["items"]


@router.get("/departments/{dept_name}", response_model=DepartmentDetailOut)
def operations_department_detail(
    dept_name: str,
    date_from: date | None = None,
    date_to: date | None = None,
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
    try:
        return get_department_operation_detail(
            db=db,
            dept_name=scoped_dept or dept_name,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
