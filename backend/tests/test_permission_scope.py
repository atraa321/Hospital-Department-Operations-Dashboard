from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.security import CurrentUser, ROLE_ADMIN, ROLE_DIRECTOR, resolve_dept_scope
from app.db.base import Base
from app.models.case_info import CaseInfo
from app.services.report_service import export_case_report_csv
from app.services.records_service import get_case_records


def _new_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(bind=engine)
    return SessionLocal


def test_resolve_dept_scope_blocks_cross_department_for_director():
    director = CurrentUser(user_id="director_a", role=ROLE_DIRECTOR, dept_name="普外科")
    assert resolve_dept_scope(None, director) == "普外科"
    assert resolve_dept_scope("普外科", director) == "普外科"

    try:
        resolve_dept_scope("儿科", director)
    except HTTPException as exc:
        assert exc.detail == "forbidden dept scope"
    else:
        raise AssertionError("director should not access another department")


def test_admin_can_keep_requested_scope():
    admin = CurrentUser(user_id="admin", role=ROLE_ADMIN, dept_name=None)
    assert resolve_dept_scope(None, admin) is None
    assert resolve_dept_scope("儿科", admin) == "儿科"


def test_department_scoped_exports_and_records():
    SessionLocal = _new_session()
    with SessionLocal() as db:
        db.add_all(
            [
                CaseInfo(
                    patient_id="P001",
                    patient_name="张三",
                    dept_name="普外科",
                    doctor_name="王医生",
                    discharge_date=date(2026, 2, 1),
                    total_cost=1000,
                    los=5,
                ),
                CaseInfo(
                    patient_id="P002",
                    patient_name="李四",
                    dept_name="儿科",
                    doctor_name="李医生",
                    discharge_date=date(2026, 2, 3),
                    total_cost=800,
                    los=4,
                ),
            ]
        )
        db.commit()

        csv_content = export_case_report_csv(db=db, masked=True, dept_name="普外科")
        assert "普外科" in csv_content
        assert "儿科" not in csv_content

        scoped_records = get_case_records(db=db, dept_name="普外科", page=1, page_size=20, masked=True)
        assert scoped_records["total"] == 1
        assert scoped_records["items"][0]["dept_name"] == "普外科"
