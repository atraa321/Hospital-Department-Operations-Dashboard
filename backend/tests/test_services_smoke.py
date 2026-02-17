from app.db.base import Base
from app.db.session import SessionLocal, engine
import app.models  # noqa: F401
from app.services.analytics_service import get_disease_priority
from app.services.dip_service import list_mappings, recalculate_mappings
from app.services.quality_service import get_quality_overview
from app.services.workflow_service import list_rules, run_detection


def test_quality_overview_basic_shape():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        data = get_quality_overview(db)
        assert "case_total" in data
        assert "orphan_fee_record_rate" in data
        assert data["case_total"] >= 0
    finally:
        db.close()


def test_dip_mapping_pipeline_smoke():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        recalc = recalculate_mappings(db, limit=50)
        assert recalc["total"] >= 0
        lst = list_mappings(db, page=1, page_size=10)
        assert "items" in lst
    finally:
        db.close()


def test_detection_pipeline_smoke():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rules = list_rules(db)
        assert len(rules["items"]) >= 1
        result = run_detection(db, limit=100)
        assert result["scanned_cases"] >= 0
        priority = get_disease_priority(db, limit=5)
        assert "items" in priority
    finally:
        db.close()
