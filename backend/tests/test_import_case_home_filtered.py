from __future__ import annotations

import io

import pandas as pd
from fastapi import UploadFile
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.models.case_info import CaseInfo
from app.models.import_batch import BatchStatus
from app.services.import_service import start_case_home_basic_import, start_case_home_filtered_import


def _build_source_excel(rows: list[dict[str, object]]) -> bytes:
    df = pd.DataFrame(rows)
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="source")
    bio.seek(0)
    return bio.getvalue()


def _build_filter_excel(patient_ids: list[str]) -> bytes:
    df = pd.DataFrame({"住院号": patient_ids})
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="filter")
    bio.seek(0)
    return bio.getvalue()


def _upload(filename: str, data: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(data))


def _new_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    return SessionLocal


def _prepare_settings(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()


def test_case_home_basic_import_success(monkeypatch, tmp_path):
    _prepare_settings(monkeypatch, tmp_path)
    SessionLocal = _new_session()

    rows = [
        {
            "住院号": "00090001",
            "姓名": "患者1",
            "性别": "男",
            "出生日期": "1980-01-02",
            "年龄": "45",
            "婚姻状况": "已婚",
            "职业": "教师",
            "现住址": "平顶山新华区",
        },
        {
            "住院号": "00090002",
            "姓名": "患者2",
            "性别": "女",
            "出生日期": "1990-06-15",
            "年龄": "35",
            "婚姻状况": "未婚",
            "职业": "护士",
            "现住址": "平顶山卫东区",
        },
    ]
    source_file = _upload("全院病案.xlsx", _build_source_excel(rows))

    with SessionLocal() as db:
        batch = start_case_home_basic_import(db, source_file=source_file)
        case_count = db.scalar(select(func.count()).select_from(CaseInfo)) or 0
        row = db.execute(select(CaseInfo).where(CaseInfo.patient_id == "90001")).scalar_one_or_none()

    assert batch.status == BatchStatus.SUCCESS.value
    assert case_count == 2
    assert row is not None
    assert row.patient_name == "患者1"
    assert row.gender == "男"
    assert row.age == 45
    assert row.occupation == "教师"
    assert row.current_address == "平顶山新华区"
    assert str(row.birth_date) == "1980-01-02"
    assert row.marital_status == "已婚"


def test_case_home_basic_import_optional_columns_missing(monkeypatch, tmp_path):
    _prepare_settings(monkeypatch, tmp_path)
    SessionLocal = _new_session()

    rows = [{"住院号": "00090001"}, {"住院号": "00090002"}]
    source_file = _upload("全院病案.xlsx", _build_source_excel(rows))

    with SessionLocal() as db:
        batch = start_case_home_basic_import(db, source_file=source_file)
        row = db.execute(select(CaseInfo).where(CaseInfo.patient_id == "90001")).scalar_one_or_none()

    assert batch.status == BatchStatus.SUCCESS.value
    assert row is not None
    assert row.gender is None
    assert row.age is None
    assert row.occupation is None
    assert row.current_address is None
    assert row.birth_date is None
    assert row.marital_status is None


def test_case_home_basic_import_required_column_missing(monkeypatch, tmp_path):
    _prepare_settings(monkeypatch, tmp_path)
    SessionLocal = _new_session()

    rows = [{"病案号": "00090001", "姓名": "患者1"}]
    source_file = _upload("全院病案.xlsx", _build_source_excel(rows))

    with SessionLocal() as db:
        batch = start_case_home_basic_import(db, source_file=source_file)
        case_count = db.scalar(select(func.count()).select_from(CaseInfo)) or 0

    assert batch.status == BatchStatus.FAILED.value
    assert "源文件缺少字段" in str(batch.error_message or "")
    assert case_count == 0


def test_case_home_basic_import_upsert(monkeypatch, tmp_path):
    _prepare_settings(monkeypatch, tmp_path)
    SessionLocal = _new_session()

    source_file_1 = _upload(
        "全院病案.xlsx",
        _build_source_excel(
            [
                {
                    "住院号": "00095555",
                    "姓名": "患者A",
                    "性别": "男",
                    "年龄": "40",
                    "职业": "司机",
                    "现住址": "地址A",
                }
            ]
        ),
    )
    source_file_2 = _upload(
        "全院病案.xlsx",
        _build_source_excel(
            [
                {
                    "住院号": "00095555",
                    "姓名": "患者B",
                    "性别": "女",
                    "年龄": "41",
                    "职业": "会计",
                    "现住址": "地址B",
                }
            ]
        ),
    )

    with SessionLocal() as db:
        batch_1 = start_case_home_basic_import(db, source_file=source_file_1)
        batch_2 = start_case_home_basic_import(db, source_file=source_file_2)
        rows = db.execute(select(CaseInfo).where(CaseInfo.patient_id == "95555")).scalars().all()
        batch_1_status = batch_1.status
        batch_2_status = batch_2.status
        batch_2_id = batch_2.batch_id

    assert batch_1_status == BatchStatus.SUCCESS.value
    assert batch_2_status == BatchStatus.SUCCESS.value
    assert len(rows) == 1
    assert rows[0].patient_name == "患者B"
    assert rows[0].gender == "女"
    assert rows[0].age == 41
    assert rows[0].occupation == "会计"
    assert rows[0].current_address == "地址B"
    assert rows[0].import_batch == batch_2_id


def test_case_home_filtered_compat_entrypoint_ignores_filter(monkeypatch, tmp_path):
    _prepare_settings(monkeypatch, tmp_path)
    SessionLocal = _new_session()

    source_file = _upload(
        "全院病案.xlsx",
        _build_source_excel([{"住院号": "00090001", "姓名": "患者1", "性别": "男"}]),
    )
    filter_file = _upload("病案出院病人.xlsx", _build_filter_excel(["00090001"]))

    with SessionLocal() as db:
        batch = start_case_home_filtered_import(db, source_file=source_file, filter_file=filter_file)
        row = db.execute(select(CaseInfo).where(CaseInfo.patient_id == "90001")).scalar_one_or_none()

    assert batch.status == BatchStatus.SUCCESS.value
    assert row is not None
    assert row.gender == "男"
