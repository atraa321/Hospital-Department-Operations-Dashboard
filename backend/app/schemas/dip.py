from datetime import date, datetime

from pydantic import BaseModel


class DipVersionItemOut(BaseModel):
    version: str
    record_count: int


class DipVersionOut(BaseModel):
    icd10_versions: list[DipVersionItemOut]
    icd9_versions: list[DipVersionItemOut]
    dip_versions: list[DipVersionItemOut]


class DipMappingItemOut(BaseModel):
    patient_id: str
    diagnosis_code: str | None
    surgery_code: str | None
    mapped_diag_code: str | None
    mapped_surgery_code: str | None
    dip_code: str | None
    dip_weight_score: float | None
    version: str | None
    status: str
    fail_reason: str | None
    source: str
    updated_at: datetime


class DipMappingListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[DipMappingItemOut]


class DipRecalcOut(BaseModel):
    total: int
    mapped: int
    unmapped: int


class DipManualFillIn(BaseModel):
    dip_code: str
    note: str | None = None
    operator: str | None = None


class DipStatsItemOut(BaseModel):
    patient_id: str
    patient_name: str | None
    dept_name: str | None
    doctor_name: str | None
    discharge_date: date | None
    main_diagnosis_code: str | None
    main_diagnosis_name: str | None
    surgery_code: str | None
    total_cost: float
    dip_code: str | None
    dip_weight_score: float | None
    dip_status: str
    payment_low: float | None
    payment_high: float | None
    payment_mid: float | None
    cost_ratio_pct: float | None
    multiplier_level: str


class DipStatsSummaryOut(BaseModel):
    total_cases: int
    grouped_cases: int
    ungrouped_cases: int
    point_value_min: float
    point_value_max: float
    expected_pay_min_total: float
    expected_pay_max_total: float
    low_count: int
    normal_count: int
    high_count: int
    ultra_high_count: int
    unknown_count: int


class DipStatsOut(BaseModel):
    summary: DipStatsSummaryOut
    total: int
    page: int
    page_size: int
    items: list[DipStatsItemOut]


class DipDepartmentListOut(BaseModel):
    items: list[str]
