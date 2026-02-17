from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.case_info import CaseInfo
from app.models.rule_hit import RuleHit
from app.services.workflow_service import list_rules, run_detection


def _new_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    return SessionLocal


def test_default_rules_include_aux_check_ratio():
    SessionLocal = _new_session()
    with SessionLocal() as db:
        rules = list_rules(db)["items"]
        codes = {str(item["rule_code"]) for item in rules}
        assert "R_COST" in codes
        assert "R_DRUG_RATIO" in codes
        assert "R_LOS" in codes
        assert "R_AUX_CHECK" in codes


def test_detection_uses_non_herb_drug_ratio_and_aux_check_ratio():
    SessionLocal = _new_session()
    with SessionLocal() as db:
        db.add_all(
            [
                CaseInfo(
                    patient_id="P1001",
                    dept_name="心内科",
                    total_cost=100,
                    drug_cost=10,
                    herb_cost=90,
                    exam_cost=10,
                    los=5,
                ),
                CaseInfo(
                    patient_id="P1002",
                    dept_name="心内科",
                    total_cost=100,
                    drug_cost=10,
                    herb_cost=0,
                    exam_cost=90,
                    los=5,
                ),
            ]
        )
        db.commit()

        result = run_detection(db, limit=100)
        assert result["scanned_cases"] == 2

        hits = db.execute(select(RuleHit)).scalars().all()
        p1001_drug_hits = [item for item in hits if item.patient_id == "P1001" and item.rule_code == "R_DRUG_RATIO"]
        p1002_aux_hits = [item for item in hits if item.patient_id == "P1002" and item.rule_code == "R_AUX_CHECK"]

        assert len(p1001_drug_hits) == 0
        assert len(p1002_aux_hits) == 1
        assert p1002_aux_hits[0].severity == "ORANGE"
