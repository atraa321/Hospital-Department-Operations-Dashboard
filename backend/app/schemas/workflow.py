from datetime import datetime

from pydantic import BaseModel


class AlertRuleIn(BaseModel):
    name: str
    metric_type: str
    yellow_threshold: float
    orange_threshold: float
    red_threshold: float
    description: str | None = None
    enabled: bool = True


class AlertRuleOut(BaseModel):
    id: int
    rule_code: str
    name: str
    metric_type: str
    yellow_threshold: float
    orange_threshold: float
    red_threshold: float
    description: str | None
    enabled: bool
    updated_at: datetime


class AlertRuleListOut(BaseModel):
    items: list[AlertRuleOut]


class DetectionOut(BaseModel):
    scanned_cases: int
    hit_count: int
    created_workorders: int


class RuleHitOut(BaseModel):
    id: int
    rule_code: str
    patient_id: str
    diagnosis_code: str | None
    dept_name: str | None
    severity: str
    metric_value: float
    threshold_value: float | None
    evidence_json: str | None
    hit_at: datetime


class RuleHitListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RuleHitOut]


class WorkOrderOut(BaseModel):
    id: int
    order_no: str
    hit_id: int | None
    rule_code: str | None
    patient_id: str | None
    dept_name: str | None
    severity: str
    assignee: str | None
    status: str
    due_at: datetime | None
    closed_at: datetime | None
    remark: str | None
    escalate_count: int
    updated_at: datetime


class WorkOrderListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[WorkOrderOut]


class WorkOrderStatusIn(BaseModel):
    status: str
    remark: str | None = None


class WorkOrderAssignIn(BaseModel):
    assignee: str
    remark: str | None = None


class WorkOrderStatsOut(BaseModel):
    total: int
    closed: int
    closed_on_time: int
    close_rate: float
    on_time_rate: float


class SlaCheckOut(BaseModel):
    overdue: int
    escalated: int
