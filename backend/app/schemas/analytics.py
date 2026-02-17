from pydantic import BaseModel


class CostStructureItemOut(BaseModel):
    name: str
    value: float


class CostStructureOut(BaseModel):
    items: list[CostStructureItemOut]


class TrendPointOut(BaseModel):
    period: str
    avg_cost: float
    avg_drug_ratio: float


class CostTrendOut(BaseModel):
    items: list[TrendPointOut]


class ClinicalTopItemOut(BaseModel):
    diagnosis_code: str
    diagnosis_name: str | None
    case_count: int


class ClinicalTopOut(BaseModel):
    items: list[ClinicalTopItemOut]


class DiseasePriorityItemOut(BaseModel):
    diagnosis_code: str
    diagnosis_name: str | None
    case_count: int
    avg_total_cost: float
    avg_los: float
    score: float
    layer: str
    case_score: float
    fee_contribution_score: float
    volatility_score: float
    reject_risk_score: float
    los_risk_score: float
    readmission_risk_score: float
    variation_risk_score: float


class DiseasePriorityOut(BaseModel):
    items: list[DiseasePriorityItemOut]
