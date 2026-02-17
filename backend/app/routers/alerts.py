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
from app.schemas.workflow import (
    AlertRuleIn,
    AlertRuleListOut,
    AlertRuleOut,
    DetectionOut,
    RuleHitListOut,
    RuleHitOut,
    SlaCheckOut,
    WorkOrderAssignIn,
    WorkOrderListOut,
    WorkOrderOut,
    WorkOrderStatsOut,
    WorkOrderStatusIn,
)
from app.services.workflow_service import (
    assign_workorder,
    get_rule_hit,
    list_rule_hits,
    list_rules,
    list_workorders,
    run_detection,
    run_sla_check,
    update_workorder_status,
    upsert_rule,
    workorder_stats,
)

alert_router = APIRouter(prefix="/alerts", tags=["alerts"])
workorder_router = APIRouter(prefix="/workorders", tags=["workorders"])


@alert_router.get("/rules", response_model=AlertRuleListOut)
def alert_rules(
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
    return list_rules(db)


@alert_router.put("/rules/{rule_code}", response_model=AlertRuleOut)
def alert_rule_upsert(
    rule_code: str,
    payload: AlertRuleIn,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_MEDICAL, ROLE_INSURANCE)),
):
    return upsert_rule(db=db, rule_code=rule_code, payload=payload.model_dump())


@alert_router.post("/run-detection", response_model=DetectionOut)
def alert_detection_run(
    limit: int = 3000,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_MEDICAL, ROLE_INSURANCE)),
):
    return run_detection(db=db, limit=limit)


@alert_router.get("/hits", response_model=RuleHitListOut)
def alert_hits(
    page: int = 1,
    page_size: int = 50,
    severity: str | None = None,
    rule_code: str | None = None,
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
    return list_rule_hits(
        db=db,
        page=page,
        page_size=page_size,
        severity=severity,
        rule_code=rule_code,
    )


@alert_router.get("/hits/{hit_id}", response_model=RuleHitOut)
def alert_hit_detail(
    hit_id: int,
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
    item = get_rule_hit(db=db, hit_id=hit_id)
    if not item:
        raise HTTPException(status_code=404, detail="hit not found")
    return item


@workorder_router.get("", response_model=WorkOrderListOut)
def workorder_list(
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    severity: str | None = None,
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
    return list_workorders(db=db, page=page, page_size=page_size, status=status, severity=severity)


@workorder_router.post("/{workorder_id}/assign", response_model=WorkOrderOut)
def workorder_assign(
    workorder_id: int,
    payload: WorkOrderAssignIn,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_DIRECTOR, ROLE_MEDICAL)),
):
    try:
        return assign_workorder(
            db=db,
            workorder_id=workorder_id,
            assignee=payload.assignee,
            remark=payload.remark,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@workorder_router.post("/{workorder_id}/status", response_model=WorkOrderOut)
def workorder_status_update(
    workorder_id: int,
    payload: WorkOrderStatusIn,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_DIRECTOR, ROLE_MEDICAL)),
):
    try:
        return update_workorder_status(
            db=db,
            workorder_id=workorder_id,
            status=payload.status,
            remark=payload.remark,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@workorder_router.post("/sla-check", response_model=SlaCheckOut)
def workorder_sla_check(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_MEDICAL, ROLE_INSURANCE)),
):
    return run_sla_check(db=db)


@workorder_router.get("/stats", response_model=WorkOrderStatsOut)
def workorder_stats_view(
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
    return workorder_stats(db=db)
