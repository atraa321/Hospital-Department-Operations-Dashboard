from datetime import date

from pydantic import BaseModel


class DirectorOverviewDiseaseOut(BaseModel):
    diagnosis_code: str
    diagnosis_name: str | None
    case_count: int
    total_cost: float
    avg_total_cost: float
    avg_los: float
    dip_sim_income: float
    dip_sim_balance: float
    anomaly_hit_count: int


class DirectorOverviewSummaryOut(BaseModel):
    total_cases: int
    total_cost: float
    avg_total_cost: float
    avg_los: float
    dip_sim_income: float
    dip_sim_balance: float
    point_value: float


class DirectorMonthlyTrendOut(BaseModel):
    period: str
    case_count: int
    total_cost: float
    avg_total_cost: float
    dip_sim_balance: float


class DirectorTopicOverviewOut(BaseModel):
    summary: DirectorOverviewSummaryOut
    diseases: list[DirectorOverviewDiseaseOut]
    monthly_trend: list[DirectorMonthlyTrendOut]


class DirectorCostStructureItemOut(BaseModel):
    name: str
    value: float
    ratio: float


class DirectorDipSummaryOut(BaseModel):
    grouped_cases: int
    ungrouped_cases: int
    grouped_rate: float
    point_value: float
    dip_sim_income: float
    dip_sim_balance: float


class DirectorDoctorCompareItemOut(BaseModel):
    doctor_name: str
    case_count: int
    avg_total_cost: float
    avg_los: float
    avg_drug_ratio: float
    avg_material_ratio: float
    dip_sim_balance: float


class DirectorAnomalyCategoryOut(BaseModel):
    rule_code: str
    rule_name: str | None
    hit_count: int
    red_count: int
    orange_count: int
    yellow_count: int


class DirectorAnomalySeverityOut(BaseModel):
    severity: str
    count: int


class DirectorDetailTopItemOut(BaseModel):
    item_code: str | None
    item_name: str
    total_amount: float
    case_count: int
    ratio: float


class DirectorTopicDetailOut(BaseModel):
    diagnosis_code: str
    diagnosis_name: str | None
    case_count: int
    total_cost: float
    avg_total_cost: float
    avg_los: float
    monthly_trend: list[DirectorMonthlyTrendOut]
    cost_structure: list[DirectorCostStructureItemOut]
    dip_summary: DirectorDipSummaryOut
    doctor_compare: list[DirectorDoctorCompareItemOut]
    anomaly_categories: list[DirectorAnomalyCategoryOut]
    anomaly_severity: list[DirectorAnomalySeverityOut]
    detail_top_items: list[DirectorDetailTopItemOut]


class DirectorPdfChartIn(BaseModel):
    chart_key: str
    title: str
    image_base64: str
    order_no: int = 0
    width: int | None = None
    height: int | None = None


class DirectorPdfExportIn(BaseModel):
    dept_name: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    point_value: float | None = None
    doctor_min_cases: int = 5
    charts: list[DirectorPdfChartIn]
