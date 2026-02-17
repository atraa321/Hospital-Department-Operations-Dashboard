from uuid import uuid4

import pandas as pd
from sqlalchemy import delete, select

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.case_info import CaseInfo
from app.models.cost_detail import CostDetail
from app.services.import_service import _import_cost_detail


def test_cost_detail_only_imports_patient_ids_from_case_info():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    case_patient_id = f"CASE_{suffix}"
    orphan_patient_id = f"ORPHAN_{suffix}"
    batch_id = str(uuid4())

    try:
        db.add(CaseInfo(patient_id=case_patient_id))
        db.commit()

        df = pd.DataFrame(
            [
                {
                    "项目名称": "床位费",
                    "收费数量": 1,
                    "收费标准": 100,
                    "收费额": 100,
                    "收费项目编码": "A001",
                    "计费单位": "次",
                    "收费科室": "普外科",
                    "住院号": case_patient_id,
                    "收费对象": "张三",
                    "brlx": "住院",
                    "费用类别": "床位费",
                },
                {
                    "项目名称": "材料费",
                    "收费数量": 2,
                    "收费标准": 50,
                    "收费额": 100,
                    "收费项目编码": "B001",
                    "计费单位": "次",
                    "收费科室": "普外科",
                    "住院号": orphan_patient_id,
                    "收费对象": "李四",
                    "brlx": "住院",
                    "费用类别": "材料费",
                },
            ]
        )

        success, issues = _import_cost_detail(db, df, batch_id)
        assert success == 1

        rows = db.execute(
            select(CostDetail).where(CostDetail.patient_id.in_([case_patient_id, orphan_patient_id]))
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].patient_id == case_patient_id
        assert any(item.error_code == "V010" and orphan_patient_id in item.message for item in issues)
    finally:
        db.execute(
            delete(CostDetail).where(CostDetail.patient_id.in_([case_patient_id, orphan_patient_id]))
        )
        db.execute(delete(CaseInfo).where(CaseInfo.patient_id.in_([case_patient_id, orphan_patient_id])))
        db.commit()
        db.close()

