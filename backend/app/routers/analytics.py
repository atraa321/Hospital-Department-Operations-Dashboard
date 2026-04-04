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
from app.schemas.analytics import ClinicalTopOut, CostStructureOut, CostTrendOut, DiseasePriorityOut
from app.services.analytics_service import (
    get_clinical_top,
    get_cost_structure,
    get_cost_trend,
    get_disease_priority,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Deprecated: these analytics endpoints reflect the old disease-focused
# frontend. New operational dashboards should consume /operations/*.

@router.get("/cost-structure", response_model=CostStructureOut, deprecated=True)
def cost_structure(
    db: Session = Depends(get_db),
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
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
    return get_cost_structure(db=db, dept_name=scoped_dept, date_from=date_from, date_to=date_to)


@router.get("/cost-trend", response_model=CostTrendOut, deprecated=True)
def cost_trend(
    db: Session = Depends(get_db),
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
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
    return get_cost_trend(db=db, dept_name=scoped_dept, date_from=date_from, date_to=date_to)


@router.get("/clinical-top", response_model=ClinicalTopOut, deprecated=True)
def clinical_top(
    db: Session = Depends(get_db),
    limit: int = 10,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
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
    return get_clinical_top(
        db=db,
        limit=limit,
        dept_name=scoped_dept,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/disease-priority", response_model=DiseasePriorityOut, deprecated=True)
def disease_priority(
    db: Session = Depends(get_db),
    limit: int = 20,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
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
    return get_disease_priority(
        db=db,
        limit=limit,
        dept_name=scoped_dept,
        date_from=date_from,
        date_to=date_to,
    )
