from datetime import datetime
import io
from uuid import uuid4

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.case_info import CaseInfo
from app.models.cost_detail import CostDetail
from app.models.import_batch import ImportBatch, ImportType
from app.models.import_issue import ImportIssue
from app.models.orphan_fee_action import OrphanFeeAction
from app.services.import_service import restore_case_cost_data_from_backup_bytes


def _build_backup_bytes(patient_id: str, batch_id: str) -> bytes:
    now = datetime.utcnow()
    case_df = pd.DataFrame(
        [
            {
                "patient_id": patient_id,
                "patient_name": "测试患者",
                "dept_name": "普外科",
                "import_batch": batch_id,
                "created_at": now,
                "updated_at": now,
            }
        ]
    )
    cost_df = pd.DataFrame(
        [
            {
                "patient_id": patient_id,
                "item_name": "床位费",
                "quantity": 1,
                "unit_price": 120,
                "amount": 120,
                "cost_category": "床位费",
                "cost_group": "服务费",
                "import_batch": batch_id,
                "created_at": now,
            }
        ]
    )
    orphan_df = pd.DataFrame(
        [
            {
                "patient_id": patient_id,
                "status": "PENDING",
                "note": "restore test",
                "operator": "tester",
                "created_at": now,
                "updated_at": now,
            }
        ]
    )
    batch_df = pd.DataFrame(
        [
            {
                "batch_id": batch_id,
                "import_type": ImportType.COST_DETAIL.value,
                "source_filename": "费用清单.xlsx",
                "stored_path": "D:/tmp/restore.xlsx",
                "status": "SUCCESS",
                "row_count": 1,
                "column_count": 10,
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            }
        ]
    )
    issue_df = pd.DataFrame(
        [
            {
                "batch_id": batch_id,
                "row_no": 2,
                "field_name": "费用类别",
                "error_code": "V009",
                "severity": "WARN",
                "message": "测试问题",
                "created_at": now,
            }
        ]
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        case_df.to_excel(writer, sheet_name="case_info", index=False)
        cost_df.to_excel(writer, sheet_name="cost_detail", index=False)
        orphan_df.to_excel(writer, sheet_name="orphan_fee_action", index=False)
        batch_df.to_excel(writer, sheet_name="import_batch", index=False)
        issue_df.to_excel(writer, sheet_name="import_issue", index=False)
    buffer.seek(0)
    return buffer.getvalue()


def test_restore_case_cost_data_from_backup_bytes_roundtrip():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)

    patient_id = f"RESTORE_{uuid4().hex[:8]}"
    batch_id = str(uuid4())
    backup_bytes = _build_backup_bytes(patient_id=patient_id, batch_id=batch_id)

    with SessionLocal() as db:
        result = restore_case_cost_data_from_backup_bytes(db, backup_bytes)
        assert result["restored_case_info"] == 1
        assert result["restored_cost_detail"] == 1
        assert result["restored_import_batch"] == 1
        assert result["restored_import_issue"] == 1

        case_row = db.execute(select(CaseInfo).where(CaseInfo.patient_id == patient_id)).scalar_one_or_none()
        assert case_row is not None
        cost_row = db.execute(select(CostDetail).where(CostDetail.patient_id == patient_id)).scalar_one_or_none()
        assert cost_row is not None
        orphan_row = db.execute(
            select(OrphanFeeAction).where(OrphanFeeAction.patient_id == patient_id)
        ).scalar_one_or_none()
        assert orphan_row is not None
        batch_row = db.execute(select(ImportBatch).where(ImportBatch.batch_id == batch_id)).scalar_one_or_none()
        assert batch_row is not None
        issue_row = db.execute(select(ImportIssue).where(ImportIssue.batch_id == batch_id)).scalar_one_or_none()
        assert issue_row is not None

