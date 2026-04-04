from __future__ import annotations

import csv
import io

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.case_info import CaseInfo
from app.models.rule_hit import RuleHit
from app.models.work_order import WorkOrder


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def get_monthly_report(db: Session) -> dict:
    period = func.date_format(CaseInfo.discharge_date, "%Y-%m")
    disease_rows = db.execute(
        select(
            period.label("period"),
            func.count().label("case_count"),
            func.avg(CaseInfo.total_cost).label("avg_cost"),
            (
                func.avg(CaseInfo.drug_cost / func.nullif(CaseInfo.total_cost, 0)) * 100
            ).label("avg_drug_ratio"),
        )
        .where(CaseInfo.discharge_date.is_not(None))
        .group_by(period)
        .order_by(period.asc())
    ).all()

    hit_period = func.date_format(RuleHit.hit_at, "%Y-%m")
    rule_rows = db.execute(
        select(
            hit_period.label("period"),
            func.count().label("hit_count"),
            func.sum(case((RuleHit.severity == "RED", 1), else_=0)).label("red_count"),
        )
        .group_by(hit_period)
        .order_by(hit_period.asc())
    ).all()

    return {
        "disease_metrics": [
            {
                "period": str(row.period),
                "case_count": int(row.case_count or 0),
                "avg_cost": round(float(row.avg_cost or 0), 2),
                "avg_drug_ratio": round(float(row.avg_drug_ratio or 0), 2),
            }
            for row in disease_rows
        ],
        "rule_metrics": [
            {
                "period": str(row.period),
                "hit_count": int(row.hit_count or 0),
                "red_count": int(row.red_count or 0),
            }
            for row in rule_rows
        ],
    }


def get_executive_brief(db: Session) -> dict:
    total_cases = db.execute(select(func.count()).select_from(CaseInfo)).scalar_one()
    avg_cost = db.execute(select(func.avg(CaseInfo.total_cost))).scalar_one()
    avg_los = db.execute(select(func.avg(CaseInfo.los))).scalar_one()
    rule_hit_total = db.execute(select(func.count()).select_from(RuleHit)).scalar_one()
    open_workorders = db.execute(
        select(func.count()).select_from(WorkOrder).where(WorkOrder.status != "CLOSED")
    ).scalar_one()
    closed = db.execute(
        select(func.count()).select_from(WorkOrder).where(WorkOrder.status == "CLOSED")
    ).scalar_one()
    total_orders = db.execute(select(func.count()).select_from(WorkOrder)).scalar_one()

    return {
        "total_cases": int(total_cases),
        "avg_cost": round(float(avg_cost or 0), 2),
        "avg_los": round(float(avg_los or 0), 2),
        "rule_hit_total": int(rule_hit_total),
        "open_workorders": int(open_workorders),
        "close_rate": _safe_rate(int(closed), int(total_orders)),
    }


def export_case_report_csv(db: Session, masked: bool = True, dept_name: str | None = None) -> str:
    stmt = select(
        CaseInfo.patient_id,
        CaseInfo.patient_name,
        CaseInfo.dept_name,
        CaseInfo.main_diagnosis_code,
        CaseInfo.main_diagnosis_name,
        CaseInfo.total_cost,
        CaseInfo.discharge_date,
    )
    if dept_name:
        stmt = stmt.where(CaseInfo.dept_name == dept_name)
    stmt = stmt.order_by(CaseInfo.discharge_date.desc()).limit(5000)
    rows = db.execute(stmt).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["patient_id", "patient_name", "dept_name", "diagnosis_code", "diagnosis_name", "total_cost", "discharge_date"])
    for row in rows:
        patient_id = str(row.patient_id or "")
        patient_name = str(row.patient_name or "")
        if masked:
            if len(patient_id) >= 6:
                patient_id = f"{patient_id[:2]}***{patient_id[-2:]}"
            if patient_name:
                patient_name = patient_name[0] + "*" * max(len(patient_name) - 1, 1)
        writer.writerow(
            [
                patient_id,
                patient_name,
                row.dept_name or "",
                row.main_diagnosis_code or "",
                row.main_diagnosis_name or "",
                round(float(row.total_cost or 0), 2),
                row.discharge_date.isoformat() if row.discharge_date else "",
            ]
        )
    content = output.getvalue()
    output.close()
    return content
