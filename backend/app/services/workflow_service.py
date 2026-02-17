from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.alert_rule import AlertRule
from app.models.case_info import CaseInfo
from app.models.rule_hit import RuleHit
from app.models.work_order import WorkOrder


DEFAULT_RULES = [
    {
        "rule_code": "R_COST",
        "name": "次均费用异常",
        "metric_type": "COST_MULTIPLE",
        "yellow_threshold": 1.3,
        "orange_threshold": 1.6,
        "red_threshold": 2.0,
        "description": "病例总费用高于科室均值倍数",
    },
    {
        "rule_code": "R_DRUG_RATIO",
        "name": "非草药药占比异常",
        "metric_type": "DRUG_RATIO",
        "yellow_threshold": 45,
        "orange_threshold": 50,
        "red_threshold": 60,
        "description": "非草药费（西药费+中成药费）占总费用比例",
    },
    {
        "rule_code": "R_AUX_CHECK",
        "name": "辅助检查占比异常",
        "metric_type": "AUX_CHECK_RATIO",
        "yellow_threshold": 80,
        "orange_threshold": 90,
        "red_threshold": 95,
        "description": "辅助检查费（检查费+检验费）占总费用比例",
    },
    {
        "rule_code": "R_LOS",
        "name": "平均住院日异常",
        "metric_type": "LOS_MULTIPLE",
        "yellow_threshold": 1.5,
        "orange_threshold": 1.8,
        "red_threshold": 2.0,
        "description": "病例住院日高于科室均值倍数",
    },
]


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _ensure_default_rules(db: Session) -> None:
    default_map = {str(item["rule_code"]).upper(): item for item in DEFAULT_RULES}
    existing_rows = db.execute(
        select(AlertRule).where(AlertRule.rule_code.in_(list(default_map.keys())))
    ).scalars().all()
    existing_codes = {str(row.rule_code).upper() for row in existing_rows}

    changed = False
    for row in existing_rows:
        code = str(row.rule_code).upper()
        if code != "R_DRUG_RATIO":
            continue
        if row.name == "药占比异常":
            row.name = "非草药药占比异常"
            changed = True
        if row.description == "药品费+草药费占总费用比例":
            row.description = "非草药费（西药费+中成药费）占总费用比例"
            changed = True

    for code, item in default_map.items():
        if code in existing_codes:
            continue
        db.add(AlertRule(**item, enabled=True))
        changed = True
    if changed:
        db.commit()


def list_rules(db: Session) -> dict:
    _ensure_default_rules(db)
    rows = db.execute(select(AlertRule).order_by(AlertRule.rule_code.asc())).scalars().all()
    return {
        "items": [
            {
                "id": row.id,
                "rule_code": row.rule_code,
                "name": row.name,
                "metric_type": row.metric_type,
                "yellow_threshold": float(row.yellow_threshold),
                "orange_threshold": float(row.orange_threshold),
                "red_threshold": float(row.red_threshold),
                "description": row.description,
                "enabled": bool(row.enabled),
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    }


def upsert_rule(
    db: Session,
    rule_code: str,
    payload: dict,
) -> dict:
    normalized = rule_code.strip().upper()
    row = db.execute(select(AlertRule).where(AlertRule.rule_code == normalized)).scalar_one_or_none()
    if not row:
        row = AlertRule(rule_code=normalized, name=payload["name"], metric_type=payload["metric_type"])
        db.add(row)

    row.name = payload["name"]
    row.metric_type = payload["metric_type"].upper()
    row.yellow_threshold = payload["yellow_threshold"]
    row.orange_threshold = payload["orange_threshold"]
    row.red_threshold = payload["red_threshold"]
    row.description = payload.get("description")
    row.enabled = payload.get("enabled", True)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "rule_code": row.rule_code,
        "name": row.name,
        "metric_type": row.metric_type,
        "yellow_threshold": float(row.yellow_threshold),
        "orange_threshold": float(row.orange_threshold),
        "red_threshold": float(row.red_threshold),
        "description": row.description,
        "enabled": bool(row.enabled),
        "updated_at": row.updated_at,
    }


def _evaluate_severity(metric_value: float, rule: AlertRule) -> tuple[str | None, float | None]:
    if metric_value >= float(rule.red_threshold):
        return "RED", float(rule.red_threshold)
    if metric_value >= float(rule.orange_threshold):
        return "ORANGE", float(rule.orange_threshold)
    if metric_value >= float(rule.yellow_threshold):
        return "YELLOW", float(rule.yellow_threshold)
    return None, None


def _due_days_by_severity(severity: str) -> int:
    if severity == "RED":
        return 7
    if severity == "ORANGE":
        return 14
    return 30


def run_detection(db: Session, limit: int = 3000) -> dict:
    _ensure_default_rules(db)
    limit = max(1, min(limit, 50000))
    rules = db.execute(select(AlertRule).where(AlertRule.enabled.is_(True))).scalars().all()
    cases = db.execute(
        select(CaseInfo).where(CaseInfo.total_cost > 0).order_by(CaseInfo.updated_at.desc()).limit(limit)
    ).scalars().all()
    if not cases:
        return {"scanned_cases": 0, "hit_count": 0, "created_workorders": 0}

    baseline_rows = db.execute(
        select(
            CaseInfo.dept_name,
            func.avg(CaseInfo.total_cost).label("avg_cost"),
            func.avg(CaseInfo.los).label("avg_los"),
        ).group_by(CaseInfo.dept_name)
    ).all()
    baseline_map = {
        str(row.dept_name or ""): {
            "avg_cost": float(row.avg_cost or 0),
            "avg_los": float(row.avg_los or 0),
        }
        for row in baseline_rows
    }

    hit_count = 0
    created_workorders = 0
    for case in cases:
        dept_key = str(case.dept_name or "")
        dept_avg = baseline_map.get(dept_key, {"avg_cost": 0.0, "avg_los": 0.0})
        for rule in rules:
            metric_type = rule.metric_type.upper()
            metric_value = 0.0
            evidence = {}
            if metric_type == "COST_MULTIPLE":
                avg_cost = dept_avg["avg_cost"]
                metric_value = float(case.total_cost or 0) / max(avg_cost, 1.0)
                evidence = {"dept_avg_cost": round(avg_cost, 2), "case_total_cost": float(case.total_cost or 0)}
            elif metric_type == "DRUG_RATIO":
                total = float(case.total_cost or 0)
                metric_value = (float(case.drug_cost or 0) / max(total, 0.01)) * 100
                evidence = {
                    "non_herb_drug_cost": float(case.drug_cost or 0),
                    "herb_cost_excluded": float(case.herb_cost or 0),
                    "total_cost": total,
                }
            elif metric_type == "AUX_CHECK_RATIO":
                total = float(case.total_cost or 0)
                metric_value = (float(case.exam_cost or 0) / max(total, 0.01)) * 100
                evidence = {
                    "aux_check_cost": float(case.exam_cost or 0),
                    "total_cost": total,
                }
            elif metric_type == "LOS_MULTIPLE":
                avg_los = dept_avg["avg_los"]
                metric_value = float(case.los or 0) / max(avg_los, 1.0)
                evidence = {"dept_avg_los": round(avg_los, 2), "case_los": float(case.los or 0)}
            else:
                continue

            severity, threshold = _evaluate_severity(metric_value, rule)
            if not severity:
                continue

            hit = RuleHit(
                rule_code=rule.rule_code,
                patient_id=case.patient_id,
                diagnosis_code=case.main_diagnosis_code,
                dept_name=case.dept_name,
                severity=severity,
                metric_value=round(metric_value, 4),
                threshold_value=threshold,
                evidence_json=str(evidence),
            )
            db.add(hit)
            db.flush()
            hit_count += 1

            open_order = db.execute(
                select(WorkOrder).where(
                    WorkOrder.patient_id == case.patient_id,
                    WorkOrder.rule_code == rule.rule_code,
                    WorkOrder.status != "CLOSED",
                )
            ).scalar_one_or_none()
            if open_order:
                continue

            due_at = datetime.utcnow() + timedelta(days=_due_days_by_severity(severity))
            order = WorkOrder(
                order_no=f"WO{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:4].upper()}",
                hit_id=hit.id,
                rule_code=rule.rule_code,
                patient_id=case.patient_id,
                dept_name=case.dept_name,
                severity=severity,
                status="TODO",
                due_at=due_at,
                remark="规则命中自动建单",
            )
            db.add(order)
            created_workorders += 1

    db.commit()
    return {
        "scanned_cases": len(cases),
        "hit_count": hit_count,
        "created_workorders": created_workorders,
    }


def list_rule_hits(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    severity: str | None = None,
    rule_code: str | None = None,
) -> dict:
    page = max(page, 1)
    page_size = max(min(page_size, 500), 1)
    stmt = select(RuleHit)
    if severity:
        stmt = stmt.where(RuleHit.severity == severity.upper())
    if rule_code:
        stmt = stmt.where(RuleHit.rule_code == rule_code.upper())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(RuleHit.hit_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": row.id,
                "rule_code": row.rule_code,
                "patient_id": row.patient_id,
                "diagnosis_code": row.diagnosis_code,
                "dept_name": row.dept_name,
                "severity": row.severity,
                "metric_value": float(row.metric_value),
                "threshold_value": float(row.threshold_value) if row.threshold_value is not None else None,
                "evidence_json": row.evidence_json,
                "hit_at": row.hit_at,
            }
            for row in rows
        ],
    }


def get_rule_hit(db: Session, hit_id: int) -> dict | None:
    row = db.execute(select(RuleHit).where(RuleHit.id == hit_id)).scalar_one_or_none()
    if not row:
        return None
    return {
        "id": row.id,
        "rule_code": row.rule_code,
        "patient_id": row.patient_id,
        "diagnosis_code": row.diagnosis_code,
        "dept_name": row.dept_name,
        "severity": row.severity,
        "metric_value": float(row.metric_value),
        "threshold_value": float(row.threshold_value) if row.threshold_value is not None else None,
        "evidence_json": row.evidence_json,
        "hit_at": row.hit_at,
    }


def list_workorders(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    severity: str | None = None,
) -> dict:
    page = max(page, 1)
    page_size = max(min(page_size, 500), 1)
    stmt = select(WorkOrder)
    if status:
        stmt = stmt.where(WorkOrder.status == status.upper())
    if severity:
        stmt = stmt.where(WorkOrder.severity == severity.upper())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(WorkOrder.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": row.id,
                "order_no": row.order_no,
                "hit_id": row.hit_id,
                "rule_code": row.rule_code,
                "patient_id": row.patient_id,
                "dept_name": row.dept_name,
                "severity": row.severity,
                "assignee": row.assignee,
                "status": row.status,
                "due_at": row.due_at,
                "closed_at": row.closed_at,
                "remark": row.remark,
                "escalate_count": row.escalate_count,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }


def assign_workorder(db: Session, workorder_id: int, assignee: str, remark: str | None = None) -> dict:
    row = db.execute(select(WorkOrder).where(WorkOrder.id == workorder_id)).scalar_one_or_none()
    if not row:
        raise ValueError("workorder not found")
    row.assignee = assignee.strip()
    if remark:
        row.remark = remark
    db.commit()
    db.refresh(row)
    return _workorder_to_dict(row)


def _workorder_to_dict(row: WorkOrder) -> dict:
    return {
        "id": row.id,
        "order_no": row.order_no,
        "hit_id": row.hit_id,
        "rule_code": row.rule_code,
        "patient_id": row.patient_id,
        "dept_name": row.dept_name,
        "severity": row.severity,
        "assignee": row.assignee,
        "status": row.status,
        "due_at": row.due_at,
        "closed_at": row.closed_at,
        "remark": row.remark,
        "escalate_count": row.escalate_count,
        "updated_at": row.updated_at,
    }


def update_workorder_status(
    db: Session,
    workorder_id: int,
    status: str,
    remark: str | None = None,
) -> dict:
    row = db.execute(select(WorkOrder).where(WorkOrder.id == workorder_id)).scalar_one_or_none()
    if not row:
        raise ValueError("workorder not found")

    target = status.upper().strip()
    transitions = {
        "TODO": {"IN_PROGRESS"},
        "IN_PROGRESS": {"REVIEW", "TODO"},
        "REVIEW": {"CLOSED", "IN_PROGRESS"},
        "CLOSED": set(),
    }
    if target not in transitions.get(row.status, set()):
        raise ValueError(f"invalid transition: {row.status} -> {target}")

    row.status = target
    if remark:
        row.remark = remark
    if target == "CLOSED":
        row.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _workorder_to_dict(row)


def run_sla_check(db: Session) -> dict:
    now = datetime.utcnow()
    rows = db.execute(
        select(WorkOrder).where(
            WorkOrder.status != "CLOSED",
            WorkOrder.due_at.is_not(None),
            WorkOrder.due_at < now,
        )
    ).scalars().all()

    overdue = len(rows)
    escalated = 0
    for row in rows:
        row.escalate_count = int(row.escalate_count or 0) + 1
        escalated += 1
    db.commit()
    return {"overdue": overdue, "escalated": escalated}


def workorder_stats(db: Session) -> dict:
    total = db.execute(select(func.count()).select_from(WorkOrder)).scalar_one()
    closed = db.execute(
        select(func.count()).select_from(WorkOrder).where(WorkOrder.status == "CLOSED")
    ).scalar_one()
    closed_on_time = db.execute(
        select(func.count())
        .select_from(WorkOrder)
        .where(
            WorkOrder.status == "CLOSED",
            WorkOrder.closed_at.is_not(None),
            WorkOrder.due_at.is_not(None),
            WorkOrder.closed_at <= WorkOrder.due_at,
        )
    ).scalar_one()

    return {
        "total": int(total),
        "closed": int(closed),
        "closed_on_time": int(closed_on_time),
        "close_rate": _safe_rate(int(closed), int(total)),
        "on_time_rate": _safe_rate(int(closed_on_time), int(closed)),
    }
