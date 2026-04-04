from __future__ import annotations

from pydantic import BaseModel


class OperationsOverviewSummaryOut(BaseModel):
    total_cases: int
    avg_cost: float
    avg_los: float
    turnover_index: float
    department_count: int
    average_score: float
    risk_department_count: int


class OperationsMonthlyTrendOut(BaseModel):
    period: str
    case_count: int
    avg_cost: float
    avg_los: float
    turnover_index: float
    issue_count: int


class DepartmentRankingItemOut(BaseModel):
    dept_name: str
    case_count: int
    avg_cost: float
    avg_los: float
    turnover_index: float
    issue_count: int
    efficiency_score: float
    revenue_score: float
    quality_score: float
    total_score: float
    summary_issue: str


class OperationsHighlightOut(BaseModel):
    label: str
    dept_name: str
    detail: str


class OperationsOverviewOut(BaseModel):
    summary: OperationsOverviewSummaryOut
    monthly_trend: list[OperationsMonthlyTrendOut]
    rankings: list[DepartmentRankingItemOut]
    highlights: list[OperationsHighlightOut]
    suggestions: list[str]


class DepartmentScoreBreakdownOut(BaseModel):
    efficiency_score: float
    revenue_score: float
    quality_score: float
    total_score: float


class DepartmentDriverOut(BaseModel):
    title: str
    detail: str
    tone: str


class DepartmentDetailSummaryOut(BaseModel):
    dept_name: str
    case_count: int
    avg_cost: float
    avg_los: float
    turnover_index: float
    issue_count: int
    score: DepartmentScoreBreakdownOut


class DepartmentCostStructureItemOut(BaseModel):
    name: str
    value: float
    ratio: float


class DepartmentDoctorCompareItemOut(BaseModel):
    doctor_name: str
    case_count: int
    avg_total_cost: float
    avg_los: float
    avg_drug_ratio: float
    avg_material_ratio: float
    issue_count: int


class DepartmentAnomalyCategoryOut(BaseModel):
    rule_code: str
    rule_name: str | None
    hit_count: int
    red_count: int
    orange_count: int
    yellow_count: int


class DepartmentDetailTopItemOut(BaseModel):
    item_code: str | None
    item_name: str
    total_amount: float
    case_count: int
    ratio: float


class DepartmentDetailOut(BaseModel):
    summary: DepartmentDetailSummaryOut
    monthly_trend: list[OperationsMonthlyTrendOut]
    cost_structure: list[DepartmentCostStructureItemOut]
    doctor_compare: list[DepartmentDoctorCompareItemOut]
    anomaly_categories: list[DepartmentAnomalyCategoryOut]
    detail_top_items: list[DepartmentDetailTopItemOut]
    score_drivers: list[DepartmentDriverOut]
    suggestions: list[str]
