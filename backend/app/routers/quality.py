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
from app.schemas.quality import (
    OrphanFeeActionIn,
    OrphanFeeActionOut,
    OrphanFeePatientListOut,
    QualityOverviewOut,
)
from app.services.quality_service import (
    get_orphan_fee_patients,
    get_quality_overview,
    set_orphan_fee_action,
)

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/overview", response_model=QualityOverviewOut)
def quality_overview(
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
    return get_quality_overview(db)


@router.get("/orphan-patients", response_model=OrphanFeePatientListOut)
def orphan_patients(
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
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
    return get_orphan_fee_patients(db=db, page=page, page_size=page_size)


@router.post("/orphan-patients/{patient_id}/action", response_model=OrphanFeeActionOut)
def orphan_patient_action(
    patient_id: str,
    payload: OrphanFeeActionIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_DIRECTOR, ROLE_MEDICAL)),
):
    try:
        return set_orphan_fee_action(
            db=db,
            patient_id=patient_id,
            status=payload.status,
            note=payload.note,
            operator=payload.operator or current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
