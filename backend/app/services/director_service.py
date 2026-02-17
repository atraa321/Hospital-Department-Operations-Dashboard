from __future__ import annotations

import base64
import binascii
import io
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert_rule import AlertRule
from app.models.case_info import CaseInfo
from app.models.cost_detail import CostDetail
from app.models.dip_mapping_result import DipMappingResult
from app.models.rule_hit import RuleHit
from app.models.system_config import SystemConfig


def _resolve_point_value(db: Session, point_value: float | None) -> float:
    if point_value is not None and point_value > 0:
        return round(float(point_value), 4)
    row = db.execute(
        select(SystemConfig.config_value).where(SystemConfig.config_key == "DIP_POINT_VALUE_BUDGET").limit(1)
    ).scalar_one_or_none()
    try:
        if row is not None:
            value = float(row)
            if value > 0:
                return round(value, 4)
    except (TypeError, ValueError):
        pass
    return 100.0


def _query_cases(
    db: Session,
    dept_name: str | None,
    date_from: date | None,
    date_to: date | None,
    diagnosis_code: str | None = None,
) -> list[CaseInfo]:
    stmt = select(CaseInfo).where(CaseInfo.main_diagnosis_code.is_not(None))
    if dept_name:
        stmt = stmt.where(CaseInfo.dept_name == dept_name)
    if date_from:
        stmt = stmt.where(CaseInfo.discharge_date >= date_from)
    if date_to:
        stmt = stmt.where(CaseInfo.discharge_date <= date_to)
    if diagnosis_code:
        stmt = stmt.where(CaseInfo.main_diagnosis_code == diagnosis_code)
    return db.execute(stmt).scalars().all()


def _query_mapping_map(db: Session, patient_ids: list[str]) -> dict[str, DipMappingResult]:
    if not patient_ids:
        return {}
    rows = db.execute(select(DipMappingResult).where(DipMappingResult.patient_id.in_(patient_ids))).scalars().all()
    return {row.patient_id: row for row in rows}


def _query_hits(db: Session, patient_ids: list[str]) -> list[RuleHit]:
    if not patient_ids:
        return []
    return db.execute(select(RuleHit).where(RuleHit.patient_id.in_(patient_ids))).scalars().all()


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def get_director_topic_overview(
    db: Session,
    dept_name: str | None,
    date_from: date | None,
    date_to: date | None,
    top_n: int = 5,
    point_value: float | None = None,
) -> dict:
    top_n = max(1, min(int(top_n), 20))
    point = _resolve_point_value(db, point_value)
    cases = _query_cases(db, dept_name, date_from, date_to)
    if not cases:
        return {
            "summary": {
                "total_cases": 0,
                "total_cost": 0.0,
                "avg_total_cost": 0.0,
                "avg_los": 0.0,
                "dip_sim_income": 0.0,
                "dip_sim_balance": 0.0,
                "point_value": point,
            },
            "diseases": [],
            "monthly_trend": [],
        }

    patient_ids = [str(item.patient_id) for item in cases]
    mapping_map = _query_mapping_map(db, patient_ids)
    hits = _query_hits(db, patient_ids)

    disease_hit_count: dict[str, int] = defaultdict(int)
    patient_diag_map = {str(item.patient_id): str(item.main_diagnosis_code or "") for item in cases}
    for hit in hits:
        diag = hit.diagnosis_code or patient_diag_map.get(str(hit.patient_id), "")
        if diag:
            disease_hit_count[str(diag)] += 1

    agg: dict[str, dict] = {}
    total_cost = 0.0
    total_los = 0.0
    total_income = 0.0

    monthly: dict[str, dict] = defaultdict(lambda: {"case_count": 0, "total_cost": 0.0, "dip_sim_balance": 0.0})
    for case in cases:
        diag = str(case.main_diagnosis_code or "")
        if not diag:
            continue
        diagnosis_name = case.main_diagnosis_name
        row = agg.setdefault(
            diag,
            {
                "diagnosis_code": diag,
                "diagnosis_name": diagnosis_name,
                "case_count": 0,
                "total_cost": 0.0,
                "total_los": 0.0,
                "dip_sim_income": 0.0,
            },
        )
        row["case_count"] += 1
        case_total = float(case.total_cost or 0)
        case_los = float(case.los or 0)
        row["total_cost"] += case_total
        row["total_los"] += case_los
        total_cost += case_total
        total_los += case_los

        mapping = mapping_map.get(str(case.patient_id))
        dip_income = 0.0
        if mapping and mapping.dip_weight_score is not None and float(mapping.dip_weight_score) > 0:
            dip_income = float(mapping.dip_weight_score) * point
        row["dip_sim_income"] += dip_income
        total_income += dip_income

        period = case.discharge_date.strftime("%Y-%m") if case.discharge_date else "未知"
        monthly_item = monthly[period]
        monthly_item["case_count"] += 1
        monthly_item["total_cost"] += case_total
        monthly_item["dip_sim_balance"] += dip_income - case_total

    diseases = []
    for diag, row in agg.items():
        case_count = int(row["case_count"])
        avg_cost = round(float(row["total_cost"]) / max(case_count, 1), 2)
        avg_los = round(float(row["total_los"]) / max(case_count, 1), 2)
        dip_income = round(float(row["dip_sim_income"]), 2)
        total_diag_cost = round(float(row["total_cost"]), 2)
        diseases.append(
            {
                "diagnosis_code": diag,
                "diagnosis_name": row["diagnosis_name"],
                "case_count": case_count,
                "total_cost": total_diag_cost,
                "avg_total_cost": avg_cost,
                "avg_los": avg_los,
                "dip_sim_income": dip_income,
                "dip_sim_balance": round(dip_income - total_diag_cost, 2),
                "anomaly_hit_count": int(disease_hit_count.get(diag, 0)),
            }
        )

    diseases.sort(key=lambda x: (x["case_count"], x["total_cost"]), reverse=True)
    diseases = diseases[:top_n]

    monthly_trend = []
    for period in sorted(monthly.keys()):
        row = monthly[period]
        count = int(row["case_count"])
        monthly_trend.append(
            {
                "period": period,
                "case_count": count,
                "total_cost": round(float(row["total_cost"]), 2),
                "avg_total_cost": round(float(row["total_cost"]) / max(count, 1), 2),
                "dip_sim_balance": round(float(row["dip_sim_balance"]), 2),
            }
        )

    total_cases = len(cases)
    total_cost = round(total_cost, 2)
    total_income = round(total_income, 2)
    return {
        "summary": {
            "total_cases": total_cases,
            "total_cost": total_cost,
            "avg_total_cost": round(total_cost / max(total_cases, 1), 2),
            "avg_los": round(total_los / max(total_cases, 1), 2),
            "dip_sim_income": total_income,
            "dip_sim_balance": round(total_income - total_cost, 2),
            "point_value": point,
        },
        "diseases": diseases,
        "monthly_trend": monthly_trend,
    }


def get_director_topic_detail(
    db: Session,
    diagnosis_code: str,
    dept_name: str | None,
    date_from: date | None,
    date_to: date | None,
    point_value: float | None = None,
    doctor_min_cases: int = 5,
    detail_top_n: int = 20,
) -> dict:
    normalized_diag = diagnosis_code.strip().upper()
    doctor_min_cases = max(1, min(int(doctor_min_cases), 100))
    detail_top_n = max(1, min(int(detail_top_n), 200))
    point = _resolve_point_value(db, point_value)
    cases = _query_cases(db, dept_name, date_from, date_to, diagnosis_code=normalized_diag)
    if not cases:
        raise ValueError("disease not found under current filters")

    patient_ids = [str(item.patient_id) for item in cases]
    mapping_map = _query_mapping_map(db, patient_ids)
    hits = _query_hits(db, patient_ids)

    total_cost = sum(float(item.total_cost or 0) for item in cases)
    total_los = sum(float(item.los or 0) for item in cases)
    case_count = len(cases)
    diagnosis_name = cases[0].main_diagnosis_name

    monthly: dict[str, dict] = defaultdict(lambda: {"case_count": 0, "total_cost": 0.0, "dip_sim_balance": 0.0})
    dip_income = 0.0
    grouped = 0
    for case in cases:
        mapping = mapping_map.get(str(case.patient_id))
        case_total = float(case.total_cost or 0)
        this_income = 0.0
        if mapping and mapping.dip_weight_score is not None and float(mapping.dip_weight_score) > 0:
            grouped += 1
            this_income = float(mapping.dip_weight_score) * point
        dip_income += this_income
        period = case.discharge_date.strftime("%Y-%m") if case.discharge_date else "未知"
        row = monthly[period]
        row["case_count"] += 1
        row["total_cost"] += case_total
        row["dip_sim_balance"] += this_income - case_total

    monthly_trend = []
    for period in sorted(monthly.keys()):
        row = monthly[period]
        count = int(row["case_count"])
        monthly_trend.append(
            {
                "period": period,
                "case_count": count,
                "total_cost": round(float(row["total_cost"]), 2),
                "avg_total_cost": round(float(row["total_cost"]) / max(count, 1), 2),
                "dip_sim_balance": round(float(row["dip_sim_balance"]), 2),
            }
        )

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
    cost_structure = []
    for label, field in cost_keys:
        value = round(sum(float(getattr(item, field) or 0) for item in cases), 2)
        cost_structure.append(
            {
                "name": label,
                "value": value,
                "ratio": _safe_ratio(value, max(total_cost, 0.01)),
            }
        )

    doctor_agg: dict[str, dict] = defaultdict(
        lambda: {
            "case_count": 0,
            "total_cost": 0.0,
            "total_los": 0.0,
            "sum_drug_ratio": 0.0,
            "sum_material_ratio": 0.0,
            "dip_sim_balance": 0.0,
        }
    )
    for case in cases:
        doctor = (case.doctor_name or "").strip() or "未分配医师"
        case_total = float(case.total_cost or 0)
        mapping = mapping_map.get(str(case.patient_id))
        this_income = 0.0
        if mapping and mapping.dip_weight_score is not None and float(mapping.dip_weight_score) > 0:
            this_income = float(mapping.dip_weight_score) * point
        item = doctor_agg[doctor]
        item["case_count"] += 1
        item["total_cost"] += case_total
        item["total_los"] += float(case.los or 0)
        item["sum_drug_ratio"] += _safe_ratio(float(case.drug_cost or 0), max(case_total, 0.01))
        item["sum_material_ratio"] += _safe_ratio(float(case.material_cost or 0), max(case_total, 0.01))
        item["dip_sim_balance"] += this_income - case_total

    doctor_compare = []
    for doctor, item in doctor_agg.items():
        c = int(item["case_count"])
        if c < doctor_min_cases:
            continue
        doctor_compare.append(
            {
                "doctor_name": doctor,
                "case_count": c,
                "avg_total_cost": round(float(item["total_cost"]) / c, 2),
                "avg_los": round(float(item["total_los"]) / c, 2),
                "avg_drug_ratio": round(float(item["sum_drug_ratio"]) / c, 2),
                "avg_material_ratio": round(float(item["sum_material_ratio"]) / c, 2),
                "dip_sim_balance": round(float(item["dip_sim_balance"]), 2),
            }
        )
    doctor_compare.sort(key=lambda x: (x["case_count"], x["avg_total_cost"]), reverse=True)

    rule_name_map = {
        str(item.rule_code): item.name
        for item in db.execute(select(AlertRule.rule_code, AlertRule.name)).all()
        if item.rule_code
    }
    anomaly_agg: dict[str, dict] = defaultdict(lambda: {"hit_count": 0, "red_count": 0, "orange_count": 0, "yellow_count": 0})
    severity_agg = {"RED": 0, "ORANGE": 0, "YELLOW": 0}
    for hit in hits:
        code = str(hit.rule_code or "UNKNOWN")
        anomaly_agg[code]["hit_count"] += 1
        sev = str(hit.severity or "").upper()
        if sev == "RED":
            anomaly_agg[code]["red_count"] += 1
            severity_agg["RED"] += 1
        elif sev == "ORANGE":
            anomaly_agg[code]["orange_count"] += 1
            severity_agg["ORANGE"] += 1
        elif sev == "YELLOW":
            anomaly_agg[code]["yellow_count"] += 1
            severity_agg["YELLOW"] += 1

    anomaly_categories = []
    for code, row in anomaly_agg.items():
        anomaly_categories.append(
            {
                "rule_code": code,
                "rule_name": rule_name_map.get(code),
                "hit_count": int(row["hit_count"]),
                "red_count": int(row["red_count"]),
                "orange_count": int(row["orange_count"]),
                "yellow_count": int(row["yellow_count"]),
            }
        )
    anomaly_categories.sort(key=lambda x: x["hit_count"], reverse=True)

    anomaly_severity = [
        {"severity": "RED", "count": int(severity_agg["RED"])},
        {"severity": "ORANGE", "count": int(severity_agg["ORANGE"])},
        {"severity": "YELLOW", "count": int(severity_agg["YELLOW"])},
    ]

    detail_rows = db.execute(
        select(CostDetail.item_code, CostDetail.item_name, CostDetail.amount, CostDetail.patient_id).where(
            CostDetail.patient_id.in_(patient_ids)
        )
    ).all()
    detail_agg: dict[tuple[str | None, str], dict] = {}
    for row in detail_rows:
        item_name = (row.item_name or "").strip()
        if not item_name:
            continue
        key = (row.item_code, item_name)
        bucket = detail_agg.setdefault(key, {"total_amount": 0.0, "patient_ids": set()})
        bucket["total_amount"] += float(row.amount or 0)
        bucket["patient_ids"].add(str(row.patient_id))

    detail_top_items = []
    for (item_code, item_name), row in detail_agg.items():
        total_amount = round(float(row["total_amount"]), 2)
        detail_top_items.append(
            {
                "item_code": item_code,
                "item_name": item_name,
                "total_amount": total_amount,
                "case_count": len(row["patient_ids"]),
                "ratio": _safe_ratio(total_amount, max(total_cost, 0.01)),
            }
        )
    detail_top_items.sort(key=lambda x: x["total_amount"], reverse=True)
    detail_top_items = detail_top_items[:detail_top_n]

    dip_income = round(dip_income, 2)
    total_cost = round(total_cost, 2)
    return {
        "diagnosis_code": normalized_diag,
        "diagnosis_name": diagnosis_name,
        "case_count": case_count,
        "total_cost": total_cost,
        "avg_total_cost": round(total_cost / max(case_count, 1), 2),
        "avg_los": round(total_los / max(case_count, 1), 2),
        "monthly_trend": monthly_trend,
        "cost_structure": cost_structure,
        "dip_summary": {
            "grouped_cases": int(grouped),
            "ungrouped_cases": int(case_count - grouped),
            "grouped_rate": _safe_ratio(grouped, max(case_count, 1)),
            "point_value": point,
            "dip_sim_income": dip_income,
            "dip_sim_balance": round(dip_income - total_cost, 2),
        },
        "doctor_compare": doctor_compare,
        "anomaly_categories": anomaly_categories,
        "anomaly_severity": anomaly_severity,
        "detail_top_items": detail_top_items,
    }


def _decode_base64_png(data: str) -> bytes:
    payload = data.strip()
    if payload.startswith("data:image/png;base64,"):
        payload = payload.split(",", 1)[1]
    try:
        return base64.b64decode(payload, validate=True)
    except binascii.Error as exc:
        raise ValueError("invalid chart image payload") from exc


def build_director_topic_pdf(
    diagnosis_code: str,
    diagnosis_name: str | None,
    charts: list[dict],
) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
        raise ValueError("reportlab not installed") from exc

    if not charts:
        raise ValueError("charts is required")

    valid_charts = sorted(charts, key=lambda x: int(x.get("order_no", 0)))
    out = io.BytesIO()
    pdf = canvas.Canvas(out, pagesize=A4)
    page_w, page_h = A4
    rendered = 0

    for idx, chart in enumerate(valid_charts, start=1):
        title = str(chart.get("title") or f"Chart {idx}")
        image_base64 = str(chart.get("image_base64") or "").strip()
        if not image_base64:
            continue
        image_bytes = _decode_base64_png(image_base64)
        image = ImageReader(io.BytesIO(image_bytes))
        img_w, img_h = image.getSize()
        max_w = page_w - 64
        max_h = page_h - 140
        scale = min(max_w / max(img_w, 1), max_h / max(img_h, 1))
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = (page_w - draw_w) / 2
        y = (page_h - draw_h) / 2 - 12

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(32, page_h - 36, title[:120])
        pdf.drawImage(image, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
        pdf.setFont("Helvetica", 9)
        footer = f"Disease: {diagnosis_code} {diagnosis_name or ''}".strip()
        pdf.drawString(32, 18, footer[:120])
        pdf.showPage()
        rendered += 1

    if rendered == 0:
        raise ValueError("charts has no valid images")

    pdf.save()
    out.seek(0)
    return out.getvalue()
