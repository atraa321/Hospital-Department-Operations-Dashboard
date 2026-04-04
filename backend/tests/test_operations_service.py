from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.alert_rule import AlertRule
from app.models.case_info import CaseInfo
from app.models.cost_detail import CostDetail
from app.models.rule_hit import RuleHit
from app.services.operations_service import (
    get_department_operation_detail,
    get_operations_overview,
    list_department_rankings,
)


def _new_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    return SessionLocal


def test_operations_overview_and_department_detail():
    SessionLocal = _new_session()
    suffix = uuid4().hex[:6]

    with SessionLocal() as db:
        db.add(
            AlertRule(
                rule_code="R_LOS",
                name="平均住院日偏高",
                metric_type="LOS",
                yellow_threshold=8,
                orange_threshold=10,
                red_threshold=12,
                enabled=True,
            )
        )

        p1 = f"GS{suffix}1"
        p2 = f"GS{suffix}2"
        p3 = f"EK{suffix}1"
        db.add_all(
            [
                CaseInfo(
                    patient_id=p1,
                    patient_name="甲",
                    dept_name="普外科",
                    doctor_name="王医生",
                    discharge_date=date(2026, 1, 10),
                    los=5,
                    total_cost=900,
                    drug_cost=180,
                    material_cost=220,
                    exam_cost=100,
                ),
                CaseInfo(
                    patient_id=p2,
                    patient_name="乙",
                    dept_name="普外科",
                    doctor_name="李医生",
                    discharge_date=date(2026, 2, 12),
                    los=6,
                    total_cost=1200,
                    drug_cost=260,
                    material_cost=260,
                    exam_cost=120,
                ),
                CaseInfo(
                    patient_id=p3,
                    patient_name="丙",
                    dept_name="儿科",
                    doctor_name="周医生",
                    discharge_date=date(2026, 2, 20),
                    los=9,
                    total_cost=1400,
                    drug_cost=420,
                    material_cost=180,
                    exam_cost=150,
                ),
            ]
        )
        db.add_all(
            [
                RuleHit(
                    rule_code="R_LOS",
                    patient_id=p2,
                    diagnosis_code="A01",
                    dept_name="普外科",
                    severity="YELLOW",
                    metric_value=6,
                    hit_at=datetime(2026, 2, 12, 10, 0, 0),
                ),
                RuleHit(
                    rule_code="R_LOS",
                    patient_id=p3,
                    diagnosis_code="B02",
                    dept_name="儿科",
                    severity="RED",
                    metric_value=9,
                    hit_at=datetime(2026, 2, 20, 10, 0, 0),
                ),
            ]
        )
        db.add_all(
            [
                CostDetail(patient_id=p1, item_code="I001", item_name="材料A", amount=220, quantity=1, unit_price=220, import_batch="b1"),
                CostDetail(patient_id=p2, item_code="I002", item_name="药品B", amount=260, quantity=1, unit_price=260, import_batch="b1"),
                CostDetail(patient_id=p3, item_code="I003", item_name="检查C", amount=150, quantity=1, unit_price=150, import_batch="b1"),
            ]
        )
        db.commit()

        overview = get_operations_overview(db=db, limit=10)
        assert overview["summary"]["total_cases"] == 3
        assert overview["summary"]["department_count"] == 2
        assert len(overview["rankings"]) == 2
        assert len(overview["suggestions"]) >= 1

        rankings = list_department_rankings(db=db, limit=10)
        assert rankings["items"][0]["dept_name"] in {"普外科", "儿科"}
        assert "total_score" in rankings["items"][0]

        detail = get_department_operation_detail(db=db, dept_name="普外科")
        assert detail["summary"]["dept_name"] == "普外科"
        assert detail["summary"]["score"]["total_score"] >= 0
        assert len(detail["monthly_trend"]) >= 1
        assert len(detail["doctor_compare"]) >= 1
        assert len(detail["score_drivers"]) >= 1
