from __future__ import annotations

from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.case_info import CaseInfo


def _base_conditions(
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    conditions = []
    if dept_name:
        conditions.append(CaseInfo.dept_name == dept_name)
    if date_from:
        conditions.append(CaseInfo.discharge_date >= date_from)
    if date_to:
        conditions.append(CaseInfo.discharge_date <= date_to)
    return conditions


def get_cost_structure(
    db: Session,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    conditions = _base_conditions(dept_name, date_from, date_to)
    stmt = select(
        func.sum(CaseInfo.drug_cost),
        func.sum(CaseInfo.herb_cost),
        func.sum(CaseInfo.material_cost),
        func.sum(CaseInfo.exam_cost),
        func.sum(CaseInfo.treatment_cost),
        func.sum(CaseInfo.surgery_cost),
        func.sum(CaseInfo.nursing_cost),
        func.sum(CaseInfo.service_cost),
        func.sum(CaseInfo.other_cost),
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))
    row = db.execute(stmt).one()
    values = [
        ("药品费", float(row[0] or 0)),
        ("草药费", float(row[1] or 0)),
        ("材料费", float(row[2] or 0)),
        ("检查费", float(row[3] or 0)),
        ("治疗费", float(row[4] or 0)),
        ("手术费", float(row[5] or 0)),
        ("护理费", float(row[6] or 0)),
        ("服务费", float(row[7] or 0)),
        ("其他费用", float(row[8] or 0)),
    ]
    return {
        "items": [{"name": name, "value": round(value, 2)} for name, value in values if value > 0]
    }


def get_cost_trend(
    db: Session,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    conditions = _base_conditions(dept_name, date_from, date_to)
    month_key = func.date_format(CaseInfo.discharge_date, "%Y-%m")
    stmt = select(
        month_key.label("period"),
        func.avg(CaseInfo.total_cost).label("avg_cost"),
        (
            func.avg(CaseInfo.drug_cost / func.nullif(CaseInfo.total_cost, 0)) * 100
        ).label("avg_drug_ratio"),
    ).where(CaseInfo.discharge_date.is_not(None))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.group_by(month_key).order_by(month_key.asc())
    rows = db.execute(stmt).all()
    return {
        "items": [
            {
                "period": str(row.period),
                "avg_cost": round(float(row.avg_cost or 0), 2),
                "avg_drug_ratio": round(float(row.avg_drug_ratio or 0), 2),
            }
            for row in rows
        ]
    }


def get_clinical_top(
    db: Session,
    limit: int = 10,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    limit = max(1, min(limit, 50))
    conditions = _base_conditions(dept_name, date_from, date_to)
    stmt = select(
        CaseInfo.main_diagnosis_code.label("diagnosis_code"),
        func.max(CaseInfo.main_diagnosis_name).label("diagnosis_name"),
        func.count().label("case_count"),
    ).where(CaseInfo.main_diagnosis_code.is_not(None))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.group_by(CaseInfo.main_diagnosis_code).order_by(func.count().desc()).limit(limit)
    rows = db.execute(stmt).all()
    return {
        "items": [
            {
                "diagnosis_code": str(row.diagnosis_code),
                "diagnosis_name": str(row.diagnosis_name) if row.diagnosis_name else None,
                "case_count": int(row.case_count or 0),
            }
            for row in rows
        ]
    }


def get_disease_priority(
    db: Session,
    limit: int = 20,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    limit = max(1, min(limit, 100))
    conditions = _base_conditions(dept_name, date_from, date_to)
    stmt = select(
        CaseInfo.main_diagnosis_code.label("diagnosis_code"),
        func.max(CaseInfo.main_diagnosis_name).label("diagnosis_name"),
        func.count().label("case_count"),
        func.count(func.distinct(CaseInfo.patient_id)).label("distinct_patient_count"),
        func.sum(CaseInfo.total_cost).label("sum_total_cost"),
        func.avg(CaseInfo.total_cost).label("avg_total_cost"),
        func.avg(CaseInfo.los).label("avg_los"),
        func.stddev_pop(CaseInfo.total_cost).label("std_total_cost"),
        func.stddev_pop(CaseInfo.los).label("std_los"),
        (
            func.avg(CaseInfo.drug_cost / func.nullif(CaseInfo.total_cost, 0)) * 100
        ).label("avg_drug_ratio"),
    ).where(CaseInfo.main_diagnosis_code.is_not(None))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.group_by(CaseInfo.main_diagnosis_code)
    rows = db.execute(stmt).all()
    if not rows:
        return {"items": []}

    max_case = max(float(row.case_count or 0) for row in rows) or 1.0
    max_cost_contribution = max(float(row.sum_total_cost or 0) for row in rows) or 1.0
    max_los = max(float(row.avg_los or 0) for row in rows) or 1.0
    max_drug_ratio = max(float(row.avg_drug_ratio or 0) for row in rows) or 1.0

    volatility_raw_list = []
    readmission_raw_list = []
    variation_raw_list = []
    for row in rows:
        avg_cost = float(row.avg_total_cost or 0)
        std_total = float(row.std_total_cost or 0)
        avg_los = float(row.avg_los or 0)
        std_los = float(row.std_los or 0)
        case_count = float(row.case_count or 0)
        distinct_patient_count = float(row.distinct_patient_count or 0)

        volatility_raw_list.append((std_total / max(avg_cost, 1.0)) * 100)
        readmission_raw_list.append(
            (max(case_count - distinct_patient_count, 0.0) / max(case_count, 1.0)) * 100
        )
        variation_raw_list.append((std_los / max(avg_los, 1.0)) * 100)

    max_volatility = max(volatility_raw_list) or 1.0
    max_readmission = max(readmission_raw_list) or 1.0
    max_variation = max(variation_raw_list) or 1.0

    scored = []
    for idx, row in enumerate(rows):
        case_score = float(row.case_count or 0) / max_case * 100
        fee_contribution_score = float(row.sum_total_cost or 0) / max_cost_contribution * 100
        volatility_score = volatility_raw_list[idx] / max_volatility * 100
        reject_risk_score = float(row.avg_drug_ratio or 0) / max_drug_ratio * 100
        los_score = float(row.avg_los or 0) / max_los * 100
        readmission_risk_score = readmission_raw_list[idx] / max_readmission * 100
        variation_risk_score = variation_raw_list[idx] / max_variation * 100

        score = round(
            case_score * 0.25
            + fee_contribution_score * 0.20
            + volatility_score * 0.15
            + reject_risk_score * 0.15
            + los_score * 0.10
            + readmission_risk_score * 0.10
            + variation_risk_score * 0.05,
            2,
        )
        if score >= 75:
            layer = "主力病种"
        elif score >= 60:
            layer = "重点病种"
        else:
            layer = "常规监测"
        scored.append(
            {
                "diagnosis_code": str(row.diagnosis_code),
                "diagnosis_name": str(row.diagnosis_name) if row.diagnosis_name else None,
                "case_count": int(row.case_count or 0),
                "avg_total_cost": round(float(row.avg_total_cost or 0), 2),
                "avg_los": round(float(row.avg_los or 0), 2),
                "score": score,
                "layer": layer,
                "case_score": round(case_score, 2),
                "fee_contribution_score": round(fee_contribution_score, 2),
                "volatility_score": round(volatility_score, 2),
                "reject_risk_score": round(reject_risk_score, 2),
                "los_risk_score": round(los_score, 2),
                "readmission_risk_score": round(readmission_risk_score, 2),
                "variation_risk_score": round(variation_risk_score, 2),
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"items": scored[:limit]}
