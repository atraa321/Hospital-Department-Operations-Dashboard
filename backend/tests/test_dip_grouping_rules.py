from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.case_info import CaseInfo
from app.models.dip_catalog import DipCatalog
from app.models.dip_mapping_result import DipMappingResult
from app.services.dip_service import recalculate_mappings


def _add_case(db, patient_id: str, diag: str, surgery: str | None):
    db.add(
        CaseInfo(
            patient_id=patient_id,
            icd_code=diag,
            main_diagnosis_code=diag,
            surgery_code=surgery,
            import_batch="batch_case",
        )
    )


def test_dip_grouping_priority_rules():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)

    suffix = uuid4().hex[:6]
    with SessionLocal() as db:
        db.add_all(
            [
                DipCatalog(
                    version="2025",
                    dip_code="A01.1:11.1100",
                    weight_score=100,
                    import_batch="batch_dip",
                ),
                DipCatalog(
                    version="2025",
                    dip_code="A01.1:22.2200_33.3300",
                    weight_score=90,
                    import_batch="batch_dip",
                ),
                DipCatalog(
                    version="2025",
                    dip_code="A01.1",
                    weight_score=80,
                    import_batch="batch_dip",
                ),
                DipCatalog(
                    version="2025",
                    dip_code="A01.9:44.4400",
                    weight_score=70,
                    import_batch="batch_dip",
                ),
                DipCatalog(
                    version="2025",
                    dip_code="A01.5",
                    weight_score=60,
                    import_batch="batch_dip",
                ),
            ]
        )

        p1 = f"P1_{suffix}"
        p2 = f"P2_{suffix}"
        p3 = f"P3_{suffix}"
        p4_op = f"P4OP_{suffix}"
        p4_icd3 = f"P4ICD3_{suffix}"
        p_un = f"PUN_{suffix}"

        _add_case(db, p1, "A01.1", "11.1100")
        _add_case(db, p2, "A01.1", "33.3300")
        _add_case(db, p3, "A01.1", None)
        _add_case(db, p4_op, "A01.8", "44.4400")
        _add_case(db, p4_icd3, "A01.7", None)
        _add_case(db, p_un, "B99.9", "11.1100")
        db.commit()

        stat = recalculate_mappings(db, limit=100)
        assert stat["mapped"] == 5
        assert stat["unmapped"] == 1

        rows = db.execute(
            select(DipMappingResult.patient_id, DipMappingResult.dip_code, DipMappingResult.status)
        ).all()
        mapping = {row.patient_id: (row.dip_code, row.status) for row in rows}

        assert mapping[p1] == ("A01.1:11.1100", "MAPPED")
        assert mapping[p2] == ("A01.1:22.2200_33.3300", "MAPPED")
        assert mapping[p3] == ("A01.1", "MAPPED")
        assert mapping[p4_op] == ("A01.9:44.4400", "MAPPED")
        assert mapping[p4_icd3] == ("A01.1", "MAPPED")
        assert mapping[p_un][1] == "UNMAPPED"
