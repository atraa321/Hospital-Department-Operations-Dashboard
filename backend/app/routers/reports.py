from datetime import datetime

from fastapi import APIRouter, Depends
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
)
from app.db.session import get_db
from app.schemas.reports import ExecutiveBriefOut, MonthlyReportOut
from app.services.report_service import export_case_report_csv, get_executive_brief, get_monthly_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly", response_model=MonthlyReportOut)
def monthly_report(
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
    return get_monthly_report(db)


@router.get("/executive", response_model=ExecutiveBriefOut)
def executive_report(
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
    return get_executive_brief(db)


@router.get("/cases.csv")
def case_report_csv(
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
    masked = current_user.role not in {ROLE_ADMIN}
    content = export_case_report_csv(db=db, masked=masked)
    filename = f"case_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
