from datetime import date, datetime
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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
from app.schemas.director import DirectorPdfExportIn, DirectorTopicDetailOut, DirectorTopicOverviewOut
from app.services.director_service import (
    build_director_topic_pdf,
    get_director_topic_detail,
    get_director_topic_overview,
)

router = APIRouter(prefix="/director/topic", tags=["director"])

# Deprecated: retained for historical report generation and staged migration.
# New department-facing analysis has moved to /operations/departments/{dept_name}.

@router.get("", response_model=DirectorTopicOverviewOut, deprecated=True)
def director_topic_overview(
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    top_n: int = 5,
    point_value: float | None = None,
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
        return get_director_topic_overview(
            db=db,
            dept_name=scoped_dept,
            date_from=date_from,
            date_to=date_to,
            top_n=top_n,
            point_value=point_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{diagnosis_code}", response_model=DirectorTopicDetailOut, deprecated=True)
def director_topic_detail(
    diagnosis_code: str,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    point_value: float | None = None,
    doctor_min_cases: int = 5,
    detail_top_n: int = 20,
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
        return get_director_topic_detail(
            db=db,
            diagnosis_code=diagnosis_code,
            dept_name=scoped_dept,
            date_from=date_from,
            date_to=date_to,
            point_value=point_value,
            doctor_min_cases=doctor_min_cases,
            detail_top_n=detail_top_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{diagnosis_code}/export/pdf", deprecated=True)
def director_topic_export_pdf(
    diagnosis_code: str,
    payload: DirectorPdfExportIn,
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
    scoped_dept = resolve_dept_scope(payload.dept_name, current_user)
    try:
        detail = get_director_topic_detail(
            db=db,
            diagnosis_code=diagnosis_code,
            dept_name=scoped_dept,
            date_from=payload.date_from,
            date_to=payload.date_to,
            point_value=payload.point_value,
            doctor_min_cases=payload.doctor_min_cases,
            detail_top_n=20,
        )
        content = build_director_topic_pdf(
            diagnosis_code=diagnosis_code,
            diagnosis_name=detail.get("diagnosis_name"),
            charts=[item.model_dump() for item in payload.charts],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_diag = re.sub(r"[^A-Za-z0-9_.-]+", "_", diagnosis_code.strip() or "disease")
    filename = f"director_topic_{safe_diag}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
