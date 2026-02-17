from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.case_info import CaseInfo
from app.models.cost_detail import CostDetail
from app.models.import_batch import BatchStatus, ImportBatch
from app.models.import_issue import ImportIssue
from app.models.orphan_fee_action import OrphanActionStatus, OrphanFeeAction

ICD_REGEX = r"^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,6})?$"


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def get_quality_overview(db: Session) -> dict:
    case_total = db.scalar(select(func.count()).select_from(CaseInfo)) or 0
    cost_detail_total = db.scalar(select(func.count()).select_from(CostDetail)) or 0
    batch_total = db.scalar(select(func.count()).select_from(ImportBatch)) or 0
    batch_failed = (
        db.scalar(
            select(func.count())
            .select_from(ImportBatch)
            .where(ImportBatch.status == BatchStatus.FAILED.value)
        )
        or 0
    )

    pk_complete = (
        db.scalar(
            select(func.count())
            .select_from(CaseInfo)
            .where(CaseInfo.patient_id.is_not(None), CaseInfo.patient_id != "")
        )
        or 0
    )

    required_complete = (
        db.scalar(
            select(func.count())
            .select_from(CaseInfo)
            .where(
                CaseInfo.patient_id.is_not(None),
                CaseInfo.patient_id != "",
                CaseInfo.admission_date.is_not(None),
                CaseInfo.discharge_date.is_not(None),
                CaseInfo.dept_name.is_not(None),
                CaseInfo.main_diagnosis_code.is_not(None),
                CaseInfo.main_diagnosis_name.is_not(None),
            )
        )
        or 0
    )

    icd_valid = (
        db.scalar(
            select(func.count())
            .select_from(CaseInfo)
            .where(
                CaseInfo.icd_code.is_not(None),
                CaseInfo.icd_code.op("REGEXP")(ICD_REGEX),
            )
        )
        or 0
    )

    detail_patient_total = (
        db.scalar(select(func.count(func.distinct(CostDetail.patient_id))).select_from(CostDetail)) or 0
    )
    detail_patient_matched = (
        db.scalar(
            select(func.count(func.distinct(CostDetail.patient_id)))
            .select_from(CostDetail)
            .join(CaseInfo, CaseInfo.patient_id == CostDetail.patient_id)
        )
        or 0
    )
    orphan_fee_patients = max(detail_patient_total - detail_patient_matched, 0)

    warning_issue_total = (
        db.scalar(
            select(func.count()).select_from(ImportIssue).where(ImportIssue.severity == "WARN")
        )
        or 0
    )
    error_issue_total = (
        db.scalar(
            select(func.count()).select_from(ImportIssue).where(ImportIssue.severity == "ERROR")
        )
        or 0
    )

    issue_rows = (
        db.execute(
            select(
                ImportIssue.error_code,
                ImportIssue.severity,
                func.count().label("count"),
            )
            .group_by(ImportIssue.error_code, ImportIssue.severity)
            .order_by(func.count().desc())
        )
        .all()
    )

    return {
        "case_total": int(case_total),
        "cost_detail_total": int(cost_detail_total),
        "batch_total": int(batch_total),
        "batch_failed": int(batch_failed),
        "pk_complete_rate": _safe_rate(int(pk_complete), int(case_total)),
        "required_complete_rate": _safe_rate(int(required_complete), int(case_total)),
        "icd_valid_rate": _safe_rate(int(icd_valid), int(case_total)),
        "orphan_fee_record_rate": _safe_rate(int(orphan_fee_patients), int(detail_patient_total)),
        "import_failure_rate": _safe_rate(int(batch_failed), int(batch_total)),
        "warning_issue_total": int(warning_issue_total),
        "error_issue_total": int(error_issue_total),
        "issues": [
            {
                "error_code": str(row.error_code),
                "severity": str(row.severity),
                "count": int(row.count),
            }
            for row in issue_rows
        ],
        "generated_at": datetime.utcnow(),
    }


def get_orphan_fee_patients(
    db: Session,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    page = max(page, 1)
    page_size = max(min(page_size, 500), 1)

    orphan_base = (
        select(
            CostDetail.patient_id.label("patient_id"),
            func.count().label("detail_count"),
            func.sum(CostDetail.amount).label("total_amount"),
            func.max(CostDetail.import_batch).label("latest_import_batch"),
            func.max(OrphanFeeAction.status).label("status"),
            func.max(OrphanFeeAction.note).label("note"),
            func.max(OrphanFeeAction.operator).label("operator"),
            func.max(OrphanFeeAction.updated_at).label("updated_at"),
        )
        .outerjoin(CaseInfo, CaseInfo.patient_id == CostDetail.patient_id)
        .outerjoin(OrphanFeeAction, OrphanFeeAction.patient_id == CostDetail.patient_id)
        .where(CaseInfo.patient_id.is_(None))
        .group_by(CostDetail.patient_id)
    )

    total = db.execute(select(func.count()).select_from(orphan_base.subquery())).scalar_one()
    rows = db.execute(
        orphan_base.order_by(func.sum(CostDetail.amount).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "patient_id": str(row.patient_id),
                "detail_count": int(row.detail_count or 0),
                "total_amount": float(row.total_amount or 0),
                "latest_import_batch": str(row.latest_import_batch) if row.latest_import_batch else None,
                "status": str(row.status or OrphanActionStatus.PENDING.value),
                "note": str(row.note) if row.note else None,
                "operator": str(row.operator) if row.operator else None,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }


def set_orphan_fee_action(
    db: Session,
    patient_id: str,
    status: str,
    note: str | None = None,
    operator: str | None = None,
) -> dict:
    valid_statuses = {item.value for item in OrphanActionStatus}
    normalized = status.upper().strip()
    if normalized not in valid_statuses:
        raise ValueError(f"invalid status: {status}")

    action = db.execute(
        select(OrphanFeeAction).where(OrphanFeeAction.patient_id == patient_id)
    ).scalar_one_or_none()
    if not action:
        action = OrphanFeeAction(patient_id=patient_id, status=normalized)
        db.add(action)

    action.status = normalized
    action.note = note.strip() if note else None
    action.operator = operator.strip() if operator else None
    db.commit()
    db.refresh(action)

    return {
        "patient_id": action.patient_id,
        "status": action.status,
        "note": action.note,
        "operator": action.operator,
        "updated_at": action.updated_at,
    }
