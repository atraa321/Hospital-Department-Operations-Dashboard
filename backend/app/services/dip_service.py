from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.case_info import CaseInfo
from app.models.dip_catalog import DipCatalog
from app.models.dip_mapping_result import DipMappingResult
from app.models.icd10_map import Icd10Map
from app.models.icd9_map import Icd9Map

MULTIPLIER_LOW = "LOW"
MULTIPLIER_NORMAL = "NORMAL"
MULTIPLIER_HIGH = "HIGH"
MULTIPLIER_ULTRA_HIGH = "ULTRA_HIGH"
MULTIPLIER_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DipRule:
    dip_code: str
    weight: float | None
    diagnosis_code: str | None
    operation_expr: str | None
    diagnosis_icd3: str | None
    operation_tokens: tuple[str, ...]


@dataclass
class DipRuleIndex:
    diag_op_exact: dict[tuple[str, str], DipRule]
    diag_op_token: dict[tuple[str, str], DipRule]
    diag_only: dict[str, DipRule]
    icd3_op_exact: dict[tuple[str, str], DipRule]
    icd3_op_token: dict[tuple[str, str], DipRule]
    icd3_only: dict[str, DipRule]
    diag_codes: set[str]
    icd3_codes: set[str]


def _normalize_code(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text or text == "NAN":
        return None
    return text


def _to_icd3(code: str | None) -> str | None:
    norm = _normalize_code(code)
    if not norm:
        return None
    return norm[:3]


def _split_operation_tokens(code: str | None) -> tuple[str, ...]:
    norm = _normalize_code(code)
    if not norm:
        return ()
    tokens = [item.strip() for item in re.split(r"[_+,]", norm) if item and item.strip()]
    return tuple(dict.fromkeys(tokens))


def _parse_dip_rule(dip_code: str, weight_score: float | None) -> DipRule:
    norm_code = _normalize_code(dip_code)
    if not norm_code:
        return DipRule(
            dip_code="",
            weight=weight_score,
            diagnosis_code=None,
            operation_expr=None,
            diagnosis_icd3=None,
            operation_tokens=(),
        )
    diagnosis_code = norm_code
    operation_expr = None
    if ":" in norm_code:
        diagnosis_code, operation_expr = norm_code.split(":", 1)
        diagnosis_code = _normalize_code(diagnosis_code)
        operation_expr = _normalize_code(operation_expr)
    return DipRule(
        dip_code=norm_code,
        weight=float(weight_score) if weight_score is not None else None,
        diagnosis_code=diagnosis_code,
        operation_expr=operation_expr,
        diagnosis_icd3=_to_icd3(diagnosis_code),
        operation_tokens=_split_operation_tokens(operation_expr),
    )


def _pick_better_rule(current: DipRule | None, candidate: DipRule) -> DipRule:
    if current is None:
        return candidate
    current_weight = float(current.weight or 0)
    candidate_weight = float(candidate.weight or 0)
    if candidate_weight > current_weight:
        return candidate
    if candidate_weight < current_weight:
        return current
    if len(candidate.dip_code) < len(current.dip_code):
        return candidate
    return current


def _pick_best_from_candidates(candidates: list[DipRule]) -> DipRule | None:
    result: DipRule | None = None
    for item in candidates:
        result = _pick_better_rule(result, item)
    return result


def _build_rule_index(rows: list[tuple[str, float | None]]) -> DipRuleIndex:
    diag_op_exact: dict[tuple[str, str], DipRule] = {}
    diag_op_token: dict[tuple[str, str], DipRule] = {}
    diag_only: dict[str, DipRule] = {}
    icd3_op_exact: dict[tuple[str, str], DipRule] = {}
    icd3_op_token: dict[tuple[str, str], DipRule] = {}
    icd3_only: dict[str, DipRule] = {}
    diag_codes: set[str] = set()
    icd3_codes: set[str] = set()

    for dip_code, weight_score in rows:
        rule = _parse_dip_rule(dip_code, weight_score)
        if not rule.diagnosis_code:
            continue
        diag_codes.add(rule.diagnosis_code)
        if rule.diagnosis_icd3:
            icd3_codes.add(rule.diagnosis_icd3)

        if rule.operation_expr:
            key = (rule.diagnosis_code, rule.operation_expr)
            diag_op_exact[key] = _pick_better_rule(diag_op_exact.get(key), rule)
            if rule.diagnosis_icd3:
                icd3_key = (rule.diagnosis_icd3, rule.operation_expr)
                icd3_op_exact[icd3_key] = _pick_better_rule(icd3_op_exact.get(icd3_key), rule)

            for token in rule.operation_tokens:
                t_key = (rule.diagnosis_code, token)
                diag_op_token[t_key] = _pick_better_rule(diag_op_token.get(t_key), rule)
                if rule.diagnosis_icd3:
                    i_key = (rule.diagnosis_icd3, token)
                    icd3_op_token[i_key] = _pick_better_rule(icd3_op_token.get(i_key), rule)
        else:
            diag_only[rule.diagnosis_code] = _pick_better_rule(diag_only.get(rule.diagnosis_code), rule)
            if rule.diagnosis_icd3:
                icd3_only[rule.diagnosis_icd3] = _pick_better_rule(icd3_only.get(rule.diagnosis_icd3), rule)

    return DipRuleIndex(
        diag_op_exact=diag_op_exact,
        diag_op_token=diag_op_token,
        diag_only=diag_only,
        icd3_op_exact=icd3_op_exact,
        icd3_op_token=icd3_op_token,
        icd3_only=icd3_only,
        diag_codes=diag_codes,
        icd3_codes=icd3_codes,
    )


def _match_dip_rule(
    mapped_diag: str | None,
    mapped_surgery: str | None,
    idx: DipRuleIndex,
) -> tuple[DipRule | None, str | None]:
    if not mapped_diag:
        return None, None

    surgery_tokens = _split_operation_tokens(mapped_surgery)

    if mapped_surgery:
        exact = idx.diag_op_exact.get((mapped_diag, mapped_surgery))
        if exact:
            return exact, "P1"

    if surgery_tokens:
        candidates = [idx.diag_op_token.get((mapped_diag, token)) for token in surgery_tokens]
        token_match = _pick_best_from_candidates([item for item in candidates if item is not None])
        if token_match:
            return token_match, "P2"

    diag_only = idx.diag_only.get(mapped_diag)
    if diag_only:
        return diag_only, "P3"

    diag_icd3 = _to_icd3(mapped_diag)
    if not diag_icd3:
        return None, None

    if mapped_surgery:
        icd3_exact = idx.icd3_op_exact.get((diag_icd3, mapped_surgery))
        if icd3_exact:
            return icd3_exact, "P4_EXACT"

    if surgery_tokens:
        candidates = [idx.icd3_op_token.get((diag_icd3, token)) for token in surgery_tokens]
        icd3_token = _pick_best_from_candidates([item for item in candidates if item is not None])
        if icd3_token:
            return icd3_token, "P4_TOKEN"

    icd3_only = idx.icd3_only.get(diag_icd3)
    if icd3_only:
        return icd3_only, "P4_ICD3"

    return None, None


def _latest_version(db: Session, model, version_field) -> str | None:
    return db.execute(
        select(version_field).select_from(model).order_by(desc(model.id)).limit(1)
    ).scalar_one_or_none()


def get_versions(db: Session) -> dict:
    def collect(model, version_field):
        rows = db.execute(
            select(version_field.label("version"), func.count().label("count"))
            .select_from(model)
            .group_by(version_field)
            .order_by(version_field.desc())
        ).all()
        return [{"version": str(row.version), "record_count": int(row.count)} for row in rows]

    return {
        "icd10_versions": collect(Icd10Map, Icd10Map.version),
        "icd9_versions": collect(Icd9Map, Icd9Map.version),
        "dip_versions": collect(DipCatalog, DipCatalog.version),
    }


def recalculate_mappings(db: Session, limit: int = 5000) -> dict:
    limit = max(1, min(limit, 50000))
    icd10_version = _latest_version(db, Icd10Map, Icd10Map.version)
    icd9_version = _latest_version(db, Icd9Map, Icd9Map.version)
    dip_version = _latest_version(db, DipCatalog, DipCatalog.version)

    icd10_map = {}
    icd9_map = {}
    rule_idx = DipRuleIndex({}, {}, {}, {}, {}, {}, set(), set())
    dip_weight_map: dict[str, float | None] = {}
    if icd10_version:
        icd10_rows = db.execute(
            select(Icd10Map.source_code, Icd10Map.target_code).where(Icd10Map.version == icd10_version)
        ).all()
        icd10_map = {
            _normalize_code(row.source_code): _normalize_code(row.target_code)
            for row in icd10_rows
            if _normalize_code(row.source_code)
        }
    if icd9_version:
        icd9_rows = db.execute(
            select(Icd9Map.source_code, Icd9Map.target_code).where(Icd9Map.version == icd9_version)
        ).all()
        icd9_map = {
            _normalize_code(row.source_code): _normalize_code(row.target_code)
            for row in icd9_rows
            if _normalize_code(row.source_code)
        }
    if dip_version:
        dip_rows = db.execute(
            select(DipCatalog.dip_code, DipCatalog.weight_score).where(DipCatalog.version == dip_version)
        ).all()
        parsed_rows = [
            (_normalize_code(row.dip_code), float(row.weight_score) if row.weight_score is not None else None)
            for row in dip_rows
            if _normalize_code(row.dip_code)
        ]
        rule_idx = _build_rule_index(parsed_rows)
        for code, weight in parsed_rows:
            if code is None:
                continue
            prev = dip_weight_map.get(code)
            if prev is None or (weight is not None and weight > prev):
                dip_weight_map[code] = weight

    cases = db.execute(
        select(CaseInfo).order_by(CaseInfo.updated_at.desc()).limit(limit)
    ).scalars().all()
    existing = db.execute(select(DipMappingResult)).scalars().all()
    existing_map = {row.patient_id: row for row in existing}

    mapped_count = 0
    unmapped_count = 0
    for case in cases:
        raw_diag = _normalize_code(case.icd_code) or _normalize_code(case.main_diagnosis_code)
        raw_surgery = _normalize_code(case.surgery_code)
        mapped_diag = icd10_map.get(raw_diag, raw_diag)
        mapped_surgery = icd9_map.get(raw_surgery, raw_surgery) if raw_surgery else None

        dip_code = None
        fail_reason = None
        if not mapped_diag:
            fail_reason = "主诊断编码缺失"
        else:
            matched_rule, _match_type = _match_dip_rule(mapped_diag, mapped_surgery, rule_idx)
            if matched_rule:
                dip_code = matched_rule.dip_code
            else:
                diag_icd3 = _to_icd3(mapped_diag)
                if mapped_diag in rule_idx.diag_codes:
                    fail_reason = "主诊断已命中但操作未命中"
                elif diag_icd3 and diag_icd3 in rule_idx.icd3_codes:
                    fail_reason = "ICD3可命中但未完成入组"
                else:
                    fail_reason = "未命中DIP目录组合"

        result = existing_map.get(case.patient_id)
        if not result:
            result = DipMappingResult(patient_id=case.patient_id)
            db.add(result)
            existing_map[case.patient_id] = result

        result.diagnosis_code = raw_diag
        result.surgery_code = raw_surgery
        result.mapped_diag_code = mapped_diag
        result.mapped_surgery_code = mapped_surgery
        result.version = dip_version
        result.import_batch = case.import_batch
        if dip_code:
            mapped_count += 1
            result.dip_code = dip_code
            result.dip_weight_score = dip_weight_map.get(dip_code)
            result.status = "MAPPED"
            result.fail_reason = None
            result.source = "AUTO"
        else:
            unmapped_count += 1
            result.dip_code = None
            result.dip_weight_score = None
            result.status = "UNMAPPED"
            result.fail_reason = fail_reason
            result.source = "AUTO"

    db.commit()
    return {"total": len(cases), "mapped": mapped_count, "unmapped": unmapped_count}


def list_mappings(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
) -> dict:
    page = max(page, 1)
    page_size = max(min(page_size, 500), 1)
    stmt = select(DipMappingResult)
    if status:
        stmt = stmt.where(DipMappingResult.status == status.upper())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(DipMappingResult.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return {
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "patient_id": row.patient_id,
                "diagnosis_code": row.diagnosis_code,
                "surgery_code": row.surgery_code,
                "mapped_diag_code": row.mapped_diag_code,
                "mapped_surgery_code": row.mapped_surgery_code,
                "dip_code": row.dip_code,
                "dip_weight_score": float(row.dip_weight_score) if row.dip_weight_score is not None else None,
                "version": row.version,
                "status": row.status,
                "fail_reason": row.fail_reason,
                "source": row.source,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }


def _classify_multiplier_level(cost_ratio_pct: float | None) -> str:
    if cost_ratio_pct is None:
        return MULTIPLIER_UNKNOWN
    if cost_ratio_pct < 50:
        return MULTIPLIER_LOW
    if cost_ratio_pct <= 110:
        return MULTIPLIER_NORMAL
    if cost_ratio_pct <= 200:
        return MULTIPLIER_HIGH
    return MULTIPLIER_ULTRA_HIGH


def get_dip_stats(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    point_value_min: float = 5.0,
    point_value_max: float = 6.0,
    multiplier_level: str | None = None,
    dept_name: str | None = None,
    ratio_min_pct: float | None = None,
    ratio_max_pct: float | None = None,
    ungrouped_only: bool = False,
) -> dict:
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 500))
    point_value_min = float(point_value_min)
    point_value_max = float(point_value_max)
    if point_value_min <= 0 or point_value_max <= 0:
        raise ValueError("point value must be greater than 0")
    if point_value_min > point_value_max:
        point_value_min, point_value_max = point_value_max, point_value_min

    if ratio_min_pct is not None:
        ratio_min_pct = float(ratio_min_pct)
    if ratio_max_pct is not None:
        ratio_max_pct = float(ratio_max_pct)
    if ratio_min_pct is not None and ratio_min_pct < 0:
        raise ValueError("ratio_min_pct must be greater than or equal to 0")
    if ratio_max_pct is not None and ratio_max_pct < 0:
        raise ValueError("ratio_max_pct must be greater than or equal to 0")
    if ratio_min_pct is not None and ratio_max_pct is not None and ratio_min_pct > ratio_max_pct:
        ratio_min_pct, ratio_max_pct = ratio_max_pct, ratio_min_pct

    level_filter = multiplier_level.strip().upper() if multiplier_level else None
    if level_filter and level_filter not in {
        MULTIPLIER_LOW,
        MULTIPLIER_NORMAL,
        MULTIPLIER_HIGH,
        MULTIPLIER_ULTRA_HIGH,
        MULTIPLIER_UNKNOWN,
    }:
        raise ValueError("invalid multiplier_level")
    dept_filter = (dept_name or "").strip()
    dept_filter_norm = dept_filter.lower()

    stmt = (
        select(CaseInfo, DipMappingResult)
        .join(DipMappingResult, DipMappingResult.patient_id == CaseInfo.patient_id, isouter=True)
        .order_by(CaseInfo.discharge_date.desc(), CaseInfo.updated_at.desc())
    )
    rows = db.execute(stmt).all()

    items: list[dict] = []
    level_counts = {
        MULTIPLIER_LOW: 0,
        MULTIPLIER_NORMAL: 0,
        MULTIPLIER_HIGH: 0,
        MULTIPLIER_ULTRA_HIGH: 0,
        MULTIPLIER_UNKNOWN: 0,
    }
    grouped_cases = 0
    expected_pay_min_total = 0.0
    expected_pay_max_total = 0.0
    for case, mapping in rows:
        dip_code = mapping.dip_code if mapping else None
        dip_weight = float(mapping.dip_weight_score) if mapping and mapping.dip_weight_score is not None else None
        total_cost = float(case.total_cost or 0)

        payment_low = None
        payment_high = None
        payment_mid = None
        cost_ratio_pct = None
        multiplier = MULTIPLIER_UNKNOWN
        is_grouped = False
        if dip_code and dip_weight is not None and dip_weight > 0:
            is_grouped = True
            grouped_cases += 1
            payment_low = round(dip_weight * point_value_min, 2)
            payment_high = round(dip_weight * point_value_max, 2)
            payment_mid = round((payment_low + payment_high) / 2, 2)
            expected_pay_min_total += payment_low
            expected_pay_max_total += payment_high
            if payment_mid > 0:
                cost_ratio_pct = round((total_cost / payment_mid) * 100, 2)
            multiplier = _classify_multiplier_level(cost_ratio_pct)

        level_counts[multiplier] += 1
        item = {
            "patient_id": case.patient_id,
            "patient_name": case.patient_name,
            "dept_name": case.dept_name,
            "doctor_name": case.doctor_name,
            "discharge_date": case.discharge_date,
            "main_diagnosis_code": case.main_diagnosis_code,
            "main_diagnosis_name": case.main_diagnosis_name,
            "surgery_code": case.surgery_code,
            "total_cost": round(total_cost, 2),
            "dip_code": dip_code,
            "dip_weight_score": round(dip_weight, 6) if dip_weight is not None else None,
            "dip_status": mapping.status if mapping else "UNMAPPED",
            "payment_low": payment_low,
            "payment_high": payment_high,
            "payment_mid": payment_mid,
            "cost_ratio_pct": cost_ratio_pct,
            "multiplier_level": multiplier,
            "is_grouped": is_grouped,
        }
        if dept_filter_norm:
            dept_value = str(item["dept_name"] or "").strip().lower()
            if dept_filter_norm not in dept_value:
                continue
        if ungrouped_only and item["is_grouped"]:
            continue
        if ratio_min_pct is not None:
            if item["cost_ratio_pct"] is None or item["cost_ratio_pct"] < ratio_min_pct:
                continue
        if ratio_max_pct is not None:
            if item["cost_ratio_pct"] is None or item["cost_ratio_pct"] > ratio_max_pct:
                continue
        if level_filter is not None and item["multiplier_level"] != level_filter:
            continue
        items.append(item)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paged = items[start:end]
    total_cases = len(rows)
    ungrouped_cases = total_cases - grouped_cases

    return {
        "summary": {
            "total_cases": int(total_cases),
            "grouped_cases": int(grouped_cases),
            "ungrouped_cases": int(ungrouped_cases),
            "point_value_min": round(point_value_min, 4),
            "point_value_max": round(point_value_max, 4),
            "expected_pay_min_total": round(expected_pay_min_total, 2),
            "expected_pay_max_total": round(expected_pay_max_total, 2),
            "low_count": int(level_counts[MULTIPLIER_LOW]),
            "normal_count": int(level_counts[MULTIPLIER_NORMAL]),
            "high_count": int(level_counts[MULTIPLIER_HIGH]),
            "ultra_high_count": int(level_counts[MULTIPLIER_ULTRA_HIGH]),
            "unknown_count": int(level_counts[MULTIPLIER_UNKNOWN]),
        },
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "items": paged,
    }


def list_departments(db: Session) -> dict:
    rows = db.execute(
        select(CaseInfo.dept_name)
        .where(CaseInfo.dept_name.is_not(None))
        .distinct()
        .order_by(CaseInfo.dept_name.asc())
    ).all()
    items = [str(row.dept_name).strip() for row in rows if row.dept_name and str(row.dept_name).strip()]
    return {"items": items}


def manual_fill_mapping(
    db: Session,
    patient_id: str,
    dip_code: str,
    note: str | None = None,
    operator: str | None = None,
) -> dict:
    norm_code = _normalize_code(dip_code)
    if not norm_code:
        raise ValueError("dip_code is required")

    dip_weight = db.execute(
        select(DipCatalog.weight_score).where(DipCatalog.dip_code == norm_code).order_by(DipCatalog.id.desc()).limit(1)
    ).scalar_one_or_none()

    result = db.execute(
        select(DipMappingResult).where(DipMappingResult.patient_id == patient_id)
    ).scalar_one_or_none()
    if not result:
        case = db.execute(select(CaseInfo).where(CaseInfo.patient_id == patient_id)).scalar_one_or_none()
        if not case:
            raise ValueError("patient_id not found")
        result = DipMappingResult(
            patient_id=patient_id,
            diagnosis_code=_normalize_code(case.icd_code) or _normalize_code(case.main_diagnosis_code),
            surgery_code=_normalize_code(case.surgery_code),
            mapped_diag_code=_normalize_code(case.icd_code) or _normalize_code(case.main_diagnosis_code),
            mapped_surgery_code=_normalize_code(case.surgery_code),
        )
        db.add(result)

    result.dip_code = norm_code
    result.dip_weight_score = float(dip_weight or 0) if dip_weight is not None else None
    result.status = "MANUAL"
    result.source = "MANUAL"
    result.fail_reason = note.strip() if note else None
    db.commit()
    db.refresh(result)

    return {
        "patient_id": result.patient_id,
        "diagnosis_code": result.diagnosis_code,
        "surgery_code": result.surgery_code,
        "mapped_diag_code": result.mapped_diag_code,
        "mapped_surgery_code": result.mapped_surgery_code,
        "dip_code": result.dip_code,
        "dip_weight_score": float(result.dip_weight_score) if result.dip_weight_score is not None else None,
        "version": result.version,
        "status": result.status,
        "fail_reason": result.fail_reason,
        "source": result.source,
        "updated_at": result.updated_at,
    }
