from __future__ import annotations

import argparse
import re

from sqlalchemy.engine.url import make_url
import mysql.connector


SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_$-]+$")
SAFE_CHARSET_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def _validate_identifier(value: str, label: str) -> str:
    if not value:
        raise ValueError(f"{label} is empty")
    if not SAFE_NAME_PATTERN.fullmatch(value):
        raise ValueError(f"{label} contains unsupported characters: {value}")
    return value


def _validate_charset(value: str) -> str:
    if not value:
        return "utf8mb4"
    if not SAFE_CHARSET_PATTERN.fullmatch(value):
        raise ValueError(f"charset contains unsupported characters: {value}")
    return value


def _build_conn_args(db_url: str) -> tuple[dict, str, str]:
    parsed = make_url(db_url)
    if not parsed.drivername.lower().startswith("mysql"):
        raise ValueError("only mysql DATABASE_URL is supported")
    database_name = _validate_identifier(parsed.database or "", "database name")
    charset = _validate_charset((parsed.query or {}).get("charset", "utf8mb4"))
    conn_args = {
        "host": parsed.host or "127.0.0.1",
        "port": int(parsed.port or 3306),
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "charset": charset,
        "use_pure": True,
    }
    return conn_args, database_name, charset


def ensure_database(database_url: str) -> None:
    conn_args, database_name, charset = _build_conn_args(database_url)
    collation = "utf8mb4_unicode_ci" if charset.lower() == "utf8mb4" else ""
    sql = f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET {charset}"
    if collation:
        sql = f"{sql} COLLATE {collation}"

    conn = mysql.connector.connect(**conn_args)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            conn.commit()
        finally:
            cursor.close()
    finally:
        conn.close()

    print(f"Database ensured: {database_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create MySQL database if it does not exist.")
    parser.add_argument("--database-url", required=True, help="SQLAlchemy DATABASE_URL")
    args = parser.parse_args()
    ensure_database(args.database_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
