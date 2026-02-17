from pydantic import BaseModel


class MonthlyMetricOut(BaseModel):
    period: str
    case_count: int
    avg_cost: float
    avg_drug_ratio: float


class RuleMonthlyOut(BaseModel):
    period: str
    hit_count: int
    red_count: int


class MonthlyReportOut(BaseModel):
    disease_metrics: list[MonthlyMetricOut]
    rule_metrics: list[RuleMonthlyOut]


class ExecutiveBriefOut(BaseModel):
    total_cases: int
    avg_cost: float
    avg_los: float
    rule_hit_total: int
    open_workorders: int
    close_rate: float
