from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.case_info import CaseInfo
from app.models.dip_mapping_result import DipMappingResult
from app.services.dip_service import get_dip_stats, list_departments


def _insert_case(db, patient_id: str, total_cost: float, dept_name: str = "普外科"):
    db.add(
        CaseInfo(
            patient_id=patient_id,
            patient_name=f"患者{patient_id[-3:]}",
            dept_name=dept_name,
            main_diagnosis_code="A00.1",
            total_cost=total_cost,
            import_batch="batch_case",
        )
    )


def test_dip_stats_multiplier_levels_and_filter():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)

    suffix = uuid4().hex[:6]
    p_low = f"PL_{suffix}"
    p_normal = f"PN_{suffix}"
    p_high = f"PH_{suffix}"
    p_ultra = f"PU_{suffix}"
    p_unknown = f"PX_{suffix}"

    with SessionLocal() as db:
        _insert_case(db, p_low, 30)
        _insert_case(db, p_normal, 80)
        _insert_case(db, p_high, 150, dept_name="神经外科")
        _insert_case(db, p_ultra, 250)
        _insert_case(db, p_unknown, 99)

        db.add_all(
            [
                DipMappingResult(patient_id=p_low, dip_code="A00.1", dip_weight_score=1, status="MAPPED"),
                DipMappingResult(patient_id=p_normal, dip_code="A00.1", dip_weight_score=1, status="MAPPED"),
                DipMappingResult(patient_id=p_high, dip_code="A00.1", dip_weight_score=1, status="MAPPED"),
                DipMappingResult(patient_id=p_ultra, dip_code="A00.1", dip_weight_score=1, status="MAPPED"),
            ]
        )
        db.commit()

        stats = get_dip_stats(
            db=db,
            page=1,
            page_size=20,
            point_value_min=100,
            point_value_max=100,
        )
        assert stats["summary"]["low_count"] == 1
        assert stats["summary"]["normal_count"] == 1
        assert stats["summary"]["high_count"] == 1
        assert stats["summary"]["ultra_high_count"] == 1
        assert stats["summary"]["unknown_count"] == 1
        assert stats["summary"]["grouped_cases"] == 4
        assert stats["summary"]["ungrouped_cases"] == 1

        filtered = get_dip_stats(
            db=db,
            page=1,
            page_size=20,
            point_value_min=100,
            point_value_max=100,
            multiplier_level="HIGH",
        )
        assert filtered["total"] == 1
        assert filtered["items"][0]["patient_id"] == p_high
        assert filtered["items"][0]["multiplier_level"] == "HIGH"

        dept_filtered = get_dip_stats(
            db=db,
            page=1,
            page_size=20,
            point_value_min=100,
            point_value_max=100,
            dept_name="神经",
        )
        assert dept_filtered["total"] == 1
        assert dept_filtered["items"][0]["patient_id"] == p_high

        ratio_filtered = get_dip_stats(
            db=db,
            page=1,
            page_size=20,
            point_value_min=100,
            point_value_max=100,
            ratio_min_pct=120,
            ratio_max_pct=180,
        )
        assert ratio_filtered["total"] == 1
        assert ratio_filtered["items"][0]["patient_id"] == p_high

        ungrouped = get_dip_stats(
            db=db,
            page=1,
            page_size=20,
            point_value_min=100,
            point_value_max=100,
            ungrouped_only=True,
        )
        assert ungrouped["total"] == 1
        assert ungrouped["items"][0]["patient_id"] == p_unknown

        dept_options = list_departments(db=db)
        assert dept_options["items"] == ["普外科", "神经外科"]
