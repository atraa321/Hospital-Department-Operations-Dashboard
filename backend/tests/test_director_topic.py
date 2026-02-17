from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.alert_rule import AlertRule
from app.models.case_info import CaseInfo
from app.models.cost_detail import CostDetail
from app.models.dip_mapping_result import DipMappingResult
from app.models.rule_hit import RuleHit
from app.models.system_config import SystemConfig
from app.services.director_service import (
    build_director_topic_pdf,
    get_director_topic_detail,
    get_director_topic_overview,
)


ONE_PIXEL_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBgN3WfUQAAAAASUVORK5CYII="
)


def _new_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    return SessionLocal


def test_director_topic_overview_and_detail_and_pdf():
    SessionLocal = _new_session()
    suffix = uuid4().hex[:6]

    with SessionLocal() as db:
        db.add(
            SystemConfig(
                config_key="DIP_POINT_VALUE_BUDGET",
                config_value="120",
                category="director",
                description="test",
                updated_by="tester",
            )
        )
        db.add_all(
            [
                AlertRule(
                    rule_code="R_COST",
                    name="次均费用异常",
                    metric_type="COST_MULTIPLE",
                    yellow_threshold=1.3,
                    orange_threshold=1.6,
                    red_threshold=2.0,
                    enabled=True,
                ),
                AlertRule(
                    rule_code="R_DRUG_RATIO",
                    name="药占比异常",
                    metric_type="DRUG_RATIO",
                    yellow_threshold=45,
                    orange_threshold=50,
                    red_threshold=60,
                    enabled=True,
                ),
            ]
        )

        p1 = f"P{suffix}01"
        p2 = f"P{suffix}02"
        p3 = f"P{suffix}03"
        db.add_all(
            [
                CaseInfo(
                    patient_id=p1,
                    patient_name="张三",
                    doctor_name="王医生",
                    dept_name="普外科",
                    discharge_date=date(2025, 12, 1),
                    main_diagnosis_code="K56.501",
                    main_diagnosis_name="腹膜粘连伴肠梗阻",
                    los=6,
                    total_cost=1000,
                    drug_cost=200,
                    material_cost=300,
                    exam_cost=100,
                ),
                CaseInfo(
                    patient_id=p2,
                    patient_name="李四",
                    doctor_name="王医生",
                    dept_name="普外科",
                    discharge_date=date(2025, 12, 8),
                    main_diagnosis_code="K56.501",
                    main_diagnosis_name="腹膜粘连伴肠梗阻",
                    los=4,
                    total_cost=800,
                    drug_cost=160,
                    material_cost=240,
                    exam_cost=80,
                ),
                CaseInfo(
                    patient_id=p3,
                    patient_name="王五",
                    doctor_name="李医生",
                    dept_name="普外科",
                    discharge_date=date(2025, 12, 18),
                    main_diagnosis_code="J15.902",
                    main_diagnosis_name="社区获得性肺炎",
                    los=5,
                    total_cost=600,
                    drug_cost=220,
                    material_cost=80,
                    exam_cost=60,
                ),
            ]
        )
        db.add_all(
            [
                DipMappingResult(patient_id=p1, dip_code="K56.501", dip_weight_score=8, status="MAPPED"),
                DipMappingResult(patient_id=p2, dip_code="K56.501", dip_weight_score=7, status="MAPPED"),
                DipMappingResult(patient_id=p3, dip_code="J15.902", dip_weight_score=4, status="MAPPED"),
            ]
        )
        db.add_all(
            [
                RuleHit(rule_code="R_COST", patient_id=p1, diagnosis_code="K56.501", severity="RED", metric_value=2.1),
                RuleHit(rule_code="R_DRUG_RATIO", patient_id=p2, diagnosis_code="K56.501", severity="YELLOW", metric_value=46),
            ]
        )
        db.add_all(
            [
                CostDetail(patient_id=p1, item_code="D001", item_name="高值耗材A", amount=300, quantity=1, unit_price=300, import_batch="b1"),
                CostDetail(patient_id=p2, item_code="D001", item_name="高值耗材A", amount=240, quantity=1, unit_price=240, import_batch="b1"),
                CostDetail(patient_id=p2, item_code="M001", item_name="药品B", amount=120, quantity=1, unit_price=120, import_batch="b1"),
            ]
        )
        db.commit()

        overview = get_director_topic_overview(
            db=db,
            dept_name="普外科",
            date_from=date(2025, 12, 1),
            date_to=date(2025, 12, 31),
            top_n=5,
            point_value=None,
        )
        assert overview["summary"]["total_cases"] == 3
        assert overview["summary"]["point_value"] == 120.0
        assert len(overview["diseases"]) == 2
        assert overview["diseases"][0]["diagnosis_code"] == "K56.501"

        detail = get_director_topic_detail(
            db=db,
            diagnosis_code="K56.501",
            dept_name="普外科",
            date_from=date(2025, 12, 1),
            date_to=date(2025, 12, 31),
            point_value=120,
            doctor_min_cases=1,
            detail_top_n=10,
        )
        assert detail["case_count"] == 2
        assert detail["dip_summary"]["grouped_cases"] == 2
        assert detail["doctor_compare"][0]["doctor_name"] == "王医生"
        assert detail["detail_top_items"][0]["item_name"] == "高值耗材A"
        assert detail["anomaly_categories"][0]["rule_code"] in {"R_COST", "R_DRUG_RATIO"}

        pdf = build_director_topic_pdf(
            diagnosis_code="K56.501",
            diagnosis_name="腹膜粘连伴肠梗阻",
            charts=[
                {
                    "chart_key": "chart_1",
                    "title": "Chart A",
                    "image_base64": f"data:image/png;base64,{ONE_PIXEL_PNG}",
                    "order_no": 1,
                }
            ],
        )
        assert len(pdf) > 100
        assert pdf.startswith(b"%PDF")


def test_director_topic_pdf_invalid_or_empty_chart():
    with pytest.raises(ValueError, match="invalid chart image payload"):
        build_director_topic_pdf(
            diagnosis_code="X01",
            diagnosis_name="demo",
            charts=[
                {
                    "chart_key": "chart_1",
                    "title": "bad chart",
                    "image_base64": "not-base64",
                    "order_no": 1,
                }
            ],
        )

    with pytest.raises(ValueError, match="charts has no valid images"):
        build_director_topic_pdf(
            diagnosis_code="X01",
            diagnosis_name="demo",
            charts=[
                {
                    "chart_key": "chart_1",
                    "title": "empty chart",
                    "image_base64": "",
                    "order_no": 1,
                }
            ],
        )
