from datetime import datetime

from pydantic import BaseModel


class QualityIssueCountOut(BaseModel):
    error_code: str
    severity: str
    count: int


class QualityOverviewOut(BaseModel):
    case_total: int
    cost_detail_total: int
    batch_total: int
    batch_failed: int
    pk_complete_rate: float
    required_complete_rate: float
    icd_valid_rate: float
    orphan_fee_record_rate: float
    import_failure_rate: float
    warning_issue_total: int
    error_issue_total: int
    issues: list[QualityIssueCountOut]
    generated_at: datetime


class OrphanFeePatientOut(BaseModel):
    patient_id: str
    detail_count: int
    total_amount: float
    latest_import_batch: str | None
    status: str
    note: str | None
    operator: str | None
    updated_at: datetime | None


class OrphanFeePatientListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[OrphanFeePatientOut]


class OrphanFeeActionIn(BaseModel):
    status: str
    note: str | None = None
    operator: str | None = None


class OrphanFeeActionOut(BaseModel):
    patient_id: str
    status: str
    note: str | None
    operator: str | None
    updated_at: datetime
