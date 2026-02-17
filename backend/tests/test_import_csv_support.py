from __future__ import annotations

import io

import pandas as pd
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.models.case_info import CaseInfo
from app.models.cost_detail import CostDetail
from app.models.import_batch import BatchStatus, ImportType
from app.services.import_service import start_import


def _new_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    return SessionLocal


def _upload_csv(
    filename: str,
    *,
    include_header: bool = True,
    encoding: str = "utf-8-sig",
) -> UploadFile:
    df = pd.DataFrame(
        [
            {
                "医师": "王医生",
                "科室编号": "101",
                "出院科室": "普外科",
                "患者姓名": "张三",
                "入院科室": "普外科",
                "出院日期": "2025-01-05",
                "入院日期": "2025-01-01",
                "住院号": "10001",
                "诊断类型": "主要诊断",
                "诊断ICD": "K56.501",
                "诊断名称": "腹膜粘连伴肠梗阻",
                "icd": "K56.501",
                "icd3": "K56",
                "手术icd": "54.9105",
                "手术名称": "腹腔穿刺术",
            }
        ]
    )
    data = df.to_csv(index=False, header=include_header).encode(encoding)
    return UploadFile(filename=filename, file=io.BytesIO(data))


def test_start_import_case_info_supports_csv(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    SessionLocal = _new_session()

    upload_file = _upload_csv("病案出院病人.csv")
    with SessionLocal() as db:
        batch = start_import(db, upload_file, ImportType.CASE_INFO)
        case_count = db.scalar(select(func.count()).select_from(CaseInfo)) or 0
        case_row = db.execute(select(CaseInfo).where(CaseInfo.patient_id == "10001")).scalar_one_or_none()

    assert batch.status == BatchStatus.SUCCESS.value
    assert batch.row_count == 1
    assert case_count == 1
    assert case_row is not None
    assert case_row.patient_name == "张三"


def test_start_import_case_info_supports_headerless_csv(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    SessionLocal = _new_session()

    upload_file = _upload_csv("病案出院病人.csv", include_header=False, encoding="gb18030")
    with SessionLocal() as db:
        batch = start_import(db, upload_file, ImportType.CASE_INFO)
        case_count = db.scalar(select(func.count()).select_from(CaseInfo)) or 0
        case_row = db.execute(select(CaseInfo).where(CaseInfo.patient_id == "10001")).scalar_one_or_none()

    assert batch.status == BatchStatus.SUCCESS.value
    assert batch.row_count == 1
    assert case_count == 1
    assert case_row is not None
    assert case_row.patient_name == "张三"


def test_start_import_case_info_supports_alias_headers(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    SessionLocal = _new_session()

    # Simulate external CSV headers:
    # 科室编码 -> 科室编号, duplicated 患者姓名 + 患者姓名.1
    # where first name is doctor and second name is patient.
    alias_df = pd.DataFrame(
        [
            {
                "患者姓名": "王医生",
                "科室编码": "101",
                "入院科室": "普外科",
                "患者姓名.1": "张三",
                "出院科室": "普外科",
                "出院日期": "2025-01-05",
                "入院日期": "2025-01-01",
                "住院号": "10001",
                "诊断类型": "主要诊断",
                "诊断ICD": "K56.501",
                "诊断名称": "腹膜粘连伴肠梗阻",
                "icd": "K56.501",
                "icd3": "K56",
                "手术icd": "54.9105",
                "手术名称": "腹腔穿刺术",
            }
        ]
    )
    upload_file = UploadFile(
        filename="病案出院病人.csv",
        file=io.BytesIO(alias_df.to_csv(index=False).encode("utf-8-sig")),
    )

    with SessionLocal() as db:
        batch = start_import(db, upload_file, ImportType.CASE_INFO)
        case_row = db.execute(select(CaseInfo).where(CaseInfo.patient_id == "10001")).scalar_one_or_none()

    assert batch.status == BatchStatus.SUCCESS.value
    assert case_row is not None
    assert case_row.doctor_name == "王医生"
    assert case_row.patient_name == "张三"


def test_start_import_cost_detail_csv_without_dept_column(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    SessionLocal = _new_session()

    detail_df = pd.DataFrame(
        [
            {
                "项目名称": "床位费",
                "收费数量": 1,
                "收费标准": 100,
                "收费额": 100,
                "收费项目编码": "A001",
                "计费单位": "次",
                "住院号": "10001",
                "收费对象": "张三",
                "brlx": "住院",
                "费用类别": "床位费",
            }
        ]
    )
    detail_file = UploadFile(
        filename="费用清单.csv",
        file=io.BytesIO(detail_df.to_csv(index=False).encode("utf-8-sig")),
    )

    with SessionLocal() as db:
        db.add(CaseInfo(patient_id="10001", patient_name="张三"))
        db.commit()
        batch = start_import(db, detail_file, ImportType.COST_DETAIL)
        detail_count = db.scalar(select(func.count()).select_from(CostDetail)) or 0

    assert batch.status == BatchStatus.SUCCESS.value
    assert detail_count == 1


def test_start_import_cost_summary_headerless_multicolumn_csv(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    SessionLocal = _new_session()

    summary_df = pd.DataFrame(
        [
            ["10001", "2024-11-29-2025-12-31", 3199.05, 1589.88],
        ]
    )
    summary_file = UploadFile(
        filename="费用_住院号.csv",
        file=io.BytesIO(summary_df.to_csv(index=False, header=False).encode("utf-8-sig")),
    )

    with SessionLocal() as db:
        db.add(CaseInfo(patient_id="10001", patient_name="张三"))
        db.commit()
        batch = start_import(db, summary_file, ImportType.COST_SUMMARY)
        row = db.execute(select(CaseInfo).where(CaseInfo.patient_id == "10001")).scalar_one()

    assert batch.status == BatchStatus.SUCCESS.value
    assert float(row.total_cost) == 3199.05
