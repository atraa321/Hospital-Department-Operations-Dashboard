from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert_rule import AlertRule
from app.models.case_info import CaseInfo
from app.models.cost_detail import CostDetail
from app.models.rule_hit import RuleHit


def _safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _safe_turnover(case_count: int, total_los: float) -> float:
    if total_los <= 0:
        return 0.0
    return round((case_count * 30) / total_los, 2)


def _normalize_metric(value: float, min_value: float, max_value: float, reverse: bool = False) -> float:
    if max_value <= min_value:
        return 100.0
    ratio = (value - min_value) / (max_value - min_value)
    score = (1 - ratio) if reverse else ratio
    return round(max(0.0, min(score * 100, 100.0)), 2)


def _query_cases(
    db: Session,
    dept_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[CaseInfo]:
    stmt = select(CaseInfo).where(CaseInfo.dept_name.is_not(None))
    if dept_name:
        stmt = stmt.where(CaseInfo.dept_name == dept_name)
    if date_from:
        stmt = stmt.where(CaseInfo.discharge_date >= date_from)
    if date_to:
        stmt = stmt.where(CaseInfo.discharge_date <= date_to)
    return db.execute(stmt).scalars().all()


def _query_hits(db: Session, patient_ids: list[str]) -> list[RuleHit]:
    if not patient_ids:
        return []
    return db.execute(select(RuleHit).where(RuleHit.patient_id.in_(patient_ids))).scalars().all()


def _query_alert_rule_names(db: Session) -> dict[str, str]:
    rows = db.execute(select(AlertRule.rule_code, AlertRule.name)).all()
    return {str(row.rule_code): str(row.name or row.rule_code) for row in rows if row.rule_code}


def _build_department_aggregates(db: Session, cases: list[CaseInfo]) -> tuple[dict[str, dict], dict[str, str]]:
    patient_ids = [str(case.patient_id) for case in cases]
    hits = _query_hits(db, patient_ids)
    hits_by_patient: dict[str, list[RuleHit]] = defaultdict(list)
    for hit in hits:
        hits_by_patient[str(hit.patient_id)].append(hit)

    dept_data: dict[str, dict] = defaultdict(
        lambda: {
            "dept_name": "",
            "case_count": 0,
            "total_cost": 0.0,
            "total_los": 0.0,
            "drug_ratio_sum": 0.0,
            "material_ratio_sum": 0.0,
            "exam_ratio_sum": 0.0,
            "issue_count": 0,
            "red_issue_count": 0,
            "doctor_case_count": defaultdict(int),
            "monthly": defaultdict(lambda: {"case_count": 0, "total_cost": 0.0, "total_los": 0.0, "issue_count": 0}),
        }
    )

    for case in cases:
        dept_name = str(case.dept_name or "").strip()
        if not dept_name:
            continue

        total_cost = float(case.total_cost or 0)
        total_los = float(case.los or 0)
        drug_cost = float(case.drug_cost or 0)
        material_cost = float(case.material_cost or 0)
        exam_cost = float(case.exam_cost or 0)
        case_hits = hits_by_patient.get(str(case.patient_id), [])

        item = dept_data[dept_name]
        item["dept_name"] = dept_name
        item["case_count"] += 1
        item["total_cost"] += total_cost
        item["total_los"] += total_los
        item["drug_ratio_sum"] += _safe_rate(drug_cost, max(total_cost, 0.01))
        item["material_ratio_sum"] += _safe_rate(material_cost, max(total_cost, 0.01))
        item["exam_ratio_sum"] += _safe_rate(exam_cost, max(total_cost, 0.01))
        item["issue_count"] += len(case_hits)
        item["red_issue_count"] += sum(1 for hit in case_hits if str(hit.severity or "").upper() == "RED")
        doctor_name = str(case.doctor_name or "").strip() or "未分配医师"
        item["doctor_case_count"][doctor_name] += 1

        period = case.discharge_date.strftime("%Y-%m") if case.discharge_date else "未知"
        month_item = item["monthly"][period]
        month_item["case_count"] += 1
        month_item["total_cost"] += total_cost
        month_item["total_los"] += total_los
        month_item["issue_count"] += len(case_hits)

    rule_name_map = _query_alert_rule_names(db)
    return dept_data, rule_name_map


def _build_rankings_from_aggregates(dept_data: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    for dept_name, item in dept_data.items():
        case_count = int(item["case_count"])
        avg_cost = round(float(item["total_cost"]) / max(case_count, 1), 2)
        avg_los = round(float(item["total_los"]) / max(case_count, 1), 2)
        turnover_index = _safe_turnover(case_count, float(item["total_los"]))
        issue_count = int(item["issue_count"])
        issue_rate = issue_count / max(case_count, 1)
        red_rate = int(item["red_issue_count"]) / max(case_count, 1)
        avg_drug_ratio = round(float(item["drug_ratio_sum"]) / max(case_count, 1), 2)
        avg_material_ratio = round(float(item["material_ratio_sum"]) / max(case_count, 1), 2)
        avg_exam_ratio = round(float(item["exam_ratio_sum"]) / max(case_count, 1), 2)
        doctor_count = len(item["doctor_case_count"])
        summary_issue = "运行稳定"
        if avg_los >= 8:
            summary_issue = "平均住院日偏高"
        elif issue_count > 0:
            summary_issue = "存在异常命中"
        elif avg_drug_ratio > 35:
            summary_issue = "药耗结构偏高"

        rows.append(
            {
                "dept_name": dept_name,
                "case_count": case_count,
                "avg_cost": avg_cost,
                "avg_los": avg_los,
                "turnover_index": turnover_index,
                "issue_count": issue_count,
                "issue_rate": issue_rate,
                "red_rate": red_rate,
                "avg_drug_ratio": avg_drug_ratio,
                "avg_material_ratio": avg_material_ratio,
                "avg_exam_ratio": avg_exam_ratio,
                "doctor_count": doctor_count,
                "summary_issue": summary_issue,
            }
        )

    if not rows:
        return []

    metric_bounds = {
        "case_count": (min(row["case_count"] for row in rows), max(row["case_count"] for row in rows)),
        "avg_los": (min(row["avg_los"] for row in rows), max(row["avg_los"] for row in rows)),
        "turnover_index": (min(row["turnover_index"] for row in rows), max(row["turnover_index"] for row in rows)),
        "avg_cost": (min(row["avg_cost"] for row in rows), max(row["avg_cost"] for row in rows)),
        "avg_drug_ratio": (min(row["avg_drug_ratio"] for row in rows), max(row["avg_drug_ratio"] for row in rows)),
        "avg_material_ratio": (min(row["avg_material_ratio"] for row in rows), max(row["avg_material_ratio"] for row in rows)),
        "issue_rate": (min(row["issue_rate"] for row in rows), max(row["issue_rate"] for row in rows)),
        "red_rate": (min(row["red_rate"] for row in rows), max(row["red_rate"] for row in rows)),
    }

    for row in rows:
        efficiency_case = _normalize_metric(row["case_count"], *metric_bounds["case_count"])
        efficiency_turnover = _normalize_metric(row["turnover_index"], *metric_bounds["turnover_index"])
        efficiency_los = _normalize_metric(row["avg_los"], *metric_bounds["avg_los"], reverse=True)
        efficiency_score = round((efficiency_case + efficiency_turnover + efficiency_los) / 3, 2)

        revenue_cost = _normalize_metric(row["avg_cost"], *metric_bounds["avg_cost"], reverse=True)
        revenue_drug = _normalize_metric(row["avg_drug_ratio"], *metric_bounds["avg_drug_ratio"], reverse=True)
        revenue_material = _normalize_metric(row["avg_material_ratio"], *metric_bounds["avg_material_ratio"], reverse=True)
        revenue_score = round((revenue_cost * 0.5) + (revenue_drug * 0.3) + (revenue_material * 0.2), 2)

        quality_issue = _normalize_metric(row["issue_rate"], *metric_bounds["issue_rate"], reverse=True)
        quality_red = _normalize_metric(row["red_rate"], *metric_bounds["red_rate"], reverse=True)
        quality_score = round((quality_issue * 0.7) + (quality_red * 0.3), 2)

        total_score = round((efficiency_score * 0.5) + (revenue_score * 0.3) + (quality_score * 0.2), 2)

        row["efficiency_score"] = efficiency_score
        row["revenue_score"] = revenue_score
        row["quality_score"] = quality_score
        row["total_score"] = total_score

    rows.sort(key=lambda item: (item["total_score"], item["case_count"]), reverse=True)
    return rows


def _build_hospital_monthly_trend(cases: list[CaseInfo], hits_by_month: dict[str, int]) -> list[dict]:
    monthly: dict[str, dict] = defaultdict(lambda: {"case_count": 0, "total_cost": 0.0, "total_los": 0.0})
    for case in cases:
        period = case.discharge_date.strftime("%Y-%m") if case.discharge_date else "未知"
        item = monthly[period]
        item["case_count"] += 1
        item["total_cost"] += float(case.total_cost or 0)
        item["total_los"] += float(case.los or 0)

    results: list[dict] = []
    for period in sorted(monthly.keys()):
        item = monthly[period]
        count = int(item["case_count"])
        total_los = float(item["total_los"])
        results.append(
            {
                "period": period,
                "case_count": count,
                "avg_cost": round(float(item["total_cost"]) / max(count, 1), 2),
                "avg_los": round(total_los / max(count, 1), 2),
                "turnover_index": _safe_turnover(count, total_los),
                "issue_count": int(hits_by_month.get(period, 0)),
            }
        )
    return results


def get_operations_overview(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 12,
) -> dict:
    limit = max(3, min(int(limit), 30))
    cases = _query_cases(db, date_from=date_from, date_to=date_to)
    dept_data, _ = _build_department_aggregates(db, cases)
    rankings = _build_rankings_from_aggregates(dept_data)

    patient_ids = [str(case.patient_id) for case in cases]
    hits = _query_hits(db, patient_ids)
    hits_by_month: dict[str, int] = defaultdict(int)
    for hit in hits:
        period = hit.hit_at.strftime("%Y-%m")
        hits_by_month[period] += 1

    total_cases = len(cases)
    total_cost = sum(float(case.total_cost or 0) for case in cases)
    total_los = sum(float(case.los or 0) for case in cases)
    average_score = round(sum(item["total_score"] for item in rankings) / max(len(rankings), 1), 2) if rankings else 0.0
    risk_departments = [item for item in rankings if item["total_score"] < 60 or item["quality_score"] < 60]

    highlights: list[dict] = []
    if rankings:
        top = rankings[0]
        bottom = rankings[-1]
        highlights.append(
            {
                "label": "高分科室",
                "dept_name": top["dept_name"],
                "detail": f"综合运营评分 {top['total_score']}，效率得分 {top['efficiency_score']}",
            }
        )
        highlights.append(
            {
                "label": "待提升科室",
                "dept_name": bottom["dept_name"],
                "detail": f"综合运营评分 {bottom['total_score']}，主要问题：{bottom['summary_issue']}",
            }
        )
        most_risky = max(rankings, key=lambda item: item["issue_count"])
        highlights.append(
            {
                "label": "风险焦点",
                "dept_name": most_risky["dept_name"],
                "detail": f"异常命中 {most_risky['issue_count']} 次，质量得分 {most_risky['quality_score']}",
            }
        )

    suggestions: list[str] = []
    if rankings:
        high_los = max(rankings, key=lambda item: item["avg_los"])
        high_drug = max(rankings, key=lambda item: item["avg_drug_ratio"])
        low_score = rankings[-1]
        suggestions.append(
            f"优先跟进 {low_score['dept_name']}，当前综合运营评分 {low_score['total_score']}，建议先处理 {low_score['summary_issue']}。"
        )
        suggestions.append(
            f"{high_los['dept_name']} 平均住院日 {high_los['avg_los']} 天，建议重点压降周转效率。"
        )
        suggestions.append(
            f"{high_drug['dept_name']} 药品占比偏高，建议复盘重点病组与高金额项目结构。"
        )

    return {
        "summary": {
            "total_cases": total_cases,
            "avg_cost": round(total_cost / max(total_cases, 1), 2),
            "avg_los": round(total_los / max(total_cases, 1), 2),
            "turnover_index": _safe_turnover(total_cases, total_los),
            "department_count": len(rankings),
            "average_score": average_score,
            "risk_department_count": len(risk_departments),
        },
        "monthly_trend": _build_hospital_monthly_trend(cases, hits_by_month),
        "rankings": rankings[:limit],
        "highlights": highlights,
        "suggestions": suggestions,
    }


def list_department_rankings(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
) -> dict:
    cases = _query_cases(db, date_from=date_from, date_to=date_to)
    dept_data, _ = _build_department_aggregates(db, cases)
    rankings = _build_rankings_from_aggregates(dept_data)
    return {"items": rankings[: max(1, min(int(limit), 100))]}


def get_department_operation_detail(
    db: Session,
    dept_name: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    dept_name = dept_name.strip()
    if not dept_name:
        raise ValueError("dept name is required")

    all_cases = _query_cases(db, date_from=date_from, date_to=date_to)
    dept_data, rule_name_map = _build_department_aggregates(db, all_cases)
    rankings = _build_rankings_from_aggregates(dept_data)
    ranking_map = {item["dept_name"]: item for item in rankings}
    ranking_item = ranking_map.get(dept_name)
    if ranking_item is None:
        raise ValueError("department not found under current filters")

    cases = _query_cases(db, dept_name=dept_name, date_from=date_from, date_to=date_to)
    patient_ids = [str(case.patient_id) for case in cases]
    hits = _query_hits(db, patient_ids)
    hits_by_patient: dict[str, list[RuleHit]] = defaultdict(list)
    for hit in hits:
        hits_by_patient[str(hit.patient_id)].append(hit)

    cost_structure = []
    total_cost = sum(float(case.total_cost or 0) for case in cases)
    cost_keys = [
        ("药品费", "drug_cost"),
        ("草药费", "herb_cost"),
        ("材料费", "material_cost"),
        ("检查费", "exam_cost"),
        ("治疗费", "treatment_cost"),
        ("手术费", "surgery_cost"),
        ("护理费", "nursing_cost"),
        ("服务费", "service_cost"),
        ("其他费用", "other_cost"),
    ]
    for label, field_name in cost_keys:
        value = round(sum(float(getattr(case, field_name) or 0) for case in cases), 2)
        cost_structure.append({"name": label, "value": value, "ratio": _safe_rate(value, max(total_cost, 0.01))})

    doctor_agg: dict[str, dict] = defaultdict(
        lambda: {
            "case_count": 0,
            "total_cost": 0.0,
            "total_los": 0.0,
            "sum_drug_ratio": 0.0,
            "sum_material_ratio": 0.0,
            "issue_count": 0,
        }
    )
    monthly: dict[str, dict] = defaultdict(lambda: {"case_count": 0, "total_cost": 0.0, "total_los": 0.0, "issue_count": 0})
    for case in cases:
        doctor_name = str(case.doctor_name or "").strip() or "未分配医师"
        total_cost_value = float(case.total_cost or 0)
        case_hits = hits_by_patient.get(str(case.patient_id), [])
        doctor_item = doctor_agg[doctor_name]
        doctor_item["case_count"] += 1
        doctor_item["total_cost"] += total_cost_value
        doctor_item["total_los"] += float(case.los or 0)
        doctor_item["sum_drug_ratio"] += _safe_rate(float(case.drug_cost or 0), max(total_cost_value, 0.01))
        doctor_item["sum_material_ratio"] += _safe_rate(float(case.material_cost or 0), max(total_cost_value, 0.01))
        doctor_item["issue_count"] += len(case_hits)

        period = case.discharge_date.strftime("%Y-%m") if case.discharge_date else "未知"
        month_item = monthly[period]
        month_item["case_count"] += 1
        month_item["total_cost"] += total_cost_value
        month_item["total_los"] += float(case.los or 0)
        month_item["issue_count"] += len(case_hits)

    doctor_compare = []
    for doctor_name, item in doctor_agg.items():
        case_count = int(item["case_count"])
        doctor_compare.append(
            {
                "doctor_name": doctor_name,
                "case_count": case_count,
                "avg_total_cost": round(float(item["total_cost"]) / max(case_count, 1), 2),
                "avg_los": round(float(item["total_los"]) / max(case_count, 1), 2),
                "avg_drug_ratio": round(float(item["sum_drug_ratio"]) / max(case_count, 1), 2),
                "avg_material_ratio": round(float(item["sum_material_ratio"]) / max(case_count, 1), 2),
                "issue_count": int(item["issue_count"]),
            }
        )
    doctor_compare.sort(key=lambda item: (item["issue_count"], item["avg_total_cost"], item["case_count"]), reverse=True)

    anomaly_agg: dict[str, dict] = defaultdict(lambda: {"hit_count": 0, "red_count": 0, "orange_count": 0, "yellow_count": 0})
    for hit in hits:
        code = str(hit.rule_code or "UNKNOWN")
        bucket = anomaly_agg[code]
        bucket["hit_count"] += 1
        severity = str(hit.severity or "").upper()
        if severity == "RED":
            bucket["red_count"] += 1
        elif severity == "ORANGE":
            bucket["orange_count"] += 1
        elif severity == "YELLOW":
            bucket["yellow_count"] += 1

    anomaly_categories = []
    for code, item in anomaly_agg.items():
        anomaly_categories.append(
            {
                "rule_code": code,
                "rule_name": rule_name_map.get(code),
                "hit_count": int(item["hit_count"]),
                "red_count": int(item["red_count"]),
                "orange_count": int(item["orange_count"]),
                "yellow_count": int(item["yellow_count"]),
            }
        )
    anomaly_categories.sort(key=lambda item: item["hit_count"], reverse=True)

    detail_rows = db.execute(
        select(CostDetail.item_code, CostDetail.item_name, CostDetail.amount, CostDetail.patient_id).where(
            CostDetail.patient_id.in_(patient_ids)
        )
    ).all()
    detail_agg: dict[tuple[str | None, str], dict] = {}
    for row in detail_rows:
        item_name = str(row.item_name or "").strip()
        if not item_name:
            continue
        key = (row.item_code, item_name)
        bucket = detail_agg.setdefault(key, {"total_amount": 0.0, "patient_ids": set()})
        bucket["total_amount"] += float(row.amount or 0)
        bucket["patient_ids"].add(str(row.patient_id))

    detail_top_items = []
    for (item_code, item_name), item in detail_agg.items():
        total_amount = round(float(item["total_amount"]), 2)
        detail_top_items.append(
            {
                "item_code": item_code,
                "item_name": item_name,
                "total_amount": total_amount,
                "case_count": len(item["patient_ids"]),
                "ratio": _safe_rate(total_amount, max(total_cost, 0.01)),
            }
        )
    detail_top_items.sort(key=lambda item: item["total_amount"], reverse=True)
    detail_top_items = detail_top_items[:15]

    monthly_trend = []
    for period in sorted(monthly.keys()):
        item = monthly[period]
        case_count = int(item["case_count"])
        total_los = float(item["total_los"])
        monthly_trend.append(
            {
                "period": period,
                "case_count": case_count,
                "avg_cost": round(float(item["total_cost"]) / max(case_count, 1), 2),
                "avg_los": round(total_los / max(case_count, 1), 2),
                "turnover_index": _safe_turnover(case_count, total_los),
                "issue_count": int(item["issue_count"]),
            }
        )

    score_drivers = []
    if ranking_item["avg_los"] >= 8:
        score_drivers.append({"title": "住院日偏高", "detail": f"当前平均住院日 {ranking_item['avg_los']} 天，压低了效率得分。", "tone": "negative"})
    else:
        score_drivers.append({"title": "周转效率较稳", "detail": f"当前周转指数 {ranking_item['turnover_index']}，效率端表现稳定。", "tone": "positive"})
    if ranking_item["avg_drug_ratio"] >= 35:
        score_drivers.append({"title": "药品结构偏高", "detail": f"药品费用占比约 {ranking_item['avg_drug_ratio']}%，影响收益得分。", "tone": "negative"})
    else:
        score_drivers.append({"title": "费用结构可控", "detail": f"药品占比 {ranking_item['avg_drug_ratio']}%，收益结构相对平稳。", "tone": "positive"})
    if ranking_item["issue_count"] > 0:
        score_drivers.append({"title": "存在质量风险", "detail": f"当前异常命中 {ranking_item['issue_count']} 次，建议优先处理高频规则。", "tone": "negative"})
    else:
        score_drivers.append({"title": "质量面较平稳", "detail": "当前统计周期内未发现明显异常命中。", "tone": "positive"})

    suggestions = []
    if doctor_compare:
        top_cost_doctor = max(doctor_compare, key=lambda item: item["avg_total_cost"])
        suggestions.append(
            f"优先复盘 {top_cost_doctor['doctor_name']} 负责病例，次均费用 {top_cost_doctor['avg_total_cost']} 元。"
        )
    if anomaly_categories:
        top_anomaly = anomaly_categories[0]
        suggestions.append(
            f"围绕规则“{top_anomaly['rule_name'] or top_anomaly['rule_code']}”做一次专项整改，本期命中 {top_anomaly['hit_count']} 次。"
        )
    if detail_top_items:
        top_item = detail_top_items[0]
        suggestions.append(
            f"重点跟踪项目“{top_item['item_name']}”，金额占比 {top_item['ratio']}%。"
        )

    return {
        "summary": {
            "dept_name": dept_name,
            "case_count": ranking_item["case_count"],
            "avg_cost": ranking_item["avg_cost"],
            "avg_los": ranking_item["avg_los"],
            "turnover_index": ranking_item["turnover_index"],
            "issue_count": ranking_item["issue_count"],
            "score": {
                "efficiency_score": ranking_item["efficiency_score"],
                "revenue_score": ranking_item["revenue_score"],
                "quality_score": ranking_item["quality_score"],
                "total_score": ranking_item["total_score"],
            },
        },
        "monthly_trend": monthly_trend,
        "cost_structure": cost_structure,
        "doctor_compare": doctor_compare[:12],
        "anomaly_categories": anomaly_categories[:8],
        "detail_top_items": detail_top_items,
        "score_drivers": score_drivers,
        "suggestions": suggestions,
    }
