from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


CASE_INFO_BASIC_COLUMN_DDL: dict[str, str] = {
    "gender": "VARCHAR(20)",
    "birth_date": "DATE",
    "age": "INTEGER",
    "marital_status": "VARCHAR(50)",
    "occupation": "VARCHAR(100)",
    "current_address": "VARCHAR(255)",
}


def ensure_case_info_basic_columns(engine: Engine) -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = inspector.get_table_names()
        if "case_info" not in table_names:
            return

        existing_columns = {
            str(item.get("name", "")).strip().lower() for item in inspector.get_columns("case_info")
        }
        for column_name, ddl in CASE_INFO_BASIC_COLUMN_DDL.items():
            if column_name.lower() in existing_columns:
                continue
            conn.execute(text(f"ALTER TABLE case_info ADD COLUMN {column_name} {ddl}"))
