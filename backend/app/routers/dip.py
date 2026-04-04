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
)
from app.db.session import get_db
from app.schemas.dip import (
    DipDepartmentListOut,
    DipManualFillIn,
    DipMappingItemOut,
    DipMappingListOut,
    DipRecalcOut,
    DipStatsOut,
    DipVersionOut,
)
from app.services.dip_service import (
    get_versions,
    get_dip_stats,
    list_mappings,
    list_departments,
    manual_fill_mapping,
    recalculate_mappings,
)

router = APIRouter(prefix="/dip", tags=["dip"])

# Deprecated: kept only for migration compatibility with the pre-operations
# frontend flow. New pages should use /operations/* instead of DIP endpoints.

@router.get("/versions", response_model=DipVersionOut, deprecated=True)
def versions(
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
    return get_versions(db)


@router.post("/mappings/recalculate", response_model=DipRecalcOut, deprecated=True)
def recalc_mappings(
    limit: int = 5000,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_MEDICAL, ROLE_INSURANCE)),
):
    return recalculate_mappings(db=db, limit=limit)


@router.get("/mappings", response_model=DipMappingListOut, deprecated=True)
def mapping_list(
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
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
    return list_mappings(db=db, page=page, page_size=page_size, status=status)


@router.get("/unmapped", response_model=DipMappingListOut, deprecated=True)
def unmapped_list(
    page: int = 1,
    page_size: int = 50,
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
    return list_mappings(db=db, page=page, page_size=page_size, status="UNMAPPED")


@router.get("/stats", response_model=DipStatsOut, deprecated=True)
def dip_stats(
    page: int = 1,
    page_size: int = 20,
    point_value_min: float = 5.0,
    point_value_max: float = 6.0,
    multiplier_level: str | None = None,
    dept_name: str | None = None,
    ratio_min_pct: float | None = None,
    ratio_max_pct: float | None = None,
    ungrouped_only: bool = False,
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
    try:
        return get_dip_stats(
            db=db,
            page=page,
            page_size=page_size,
            point_value_min=point_value_min,
            point_value_max=point_value_max,
            multiplier_level=multiplier_level,
            dept_name=dept_name,
            ratio_min_pct=ratio_min_pct,
            ratio_max_pct=ratio_max_pct,
            ungrouped_only=ungrouped_only,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/departments", response_model=DipDepartmentListOut, deprecated=True)
def dip_departments(
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
    return list_departments(db=db)


@router.post("/unmapped/{patient_id}/manual-fill", response_model=DipMappingItemOut, deprecated=True)
def unmapped_manual_fill(
    patient_id: str,
    payload: DipManualFillIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_DIRECTOR, ROLE_MEDICAL, ROLE_INSURANCE)),
):
    try:
        return manual_fill_mapping(
            db=db,
            patient_id=patient_id,
            dip_code=payload.dip_code,
            note=payload.note,
            operator=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
