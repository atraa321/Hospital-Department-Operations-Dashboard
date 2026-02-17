from __future__ import annotations

import argparse

from sqlalchemy.engine.url import make_url


def _has_non_latin_chars(value: str | None) -> bool:
    if not value:
        return False
    return any(ord(ch) > 255 for ch in value)


def normalize_database_url(db_url: str) -> str:
    parsed = make_url(db_url)
    driver = (parsed.drivername or "").lower()
    password = parsed.password

    # PyMySQL cannot handle non-latin password chars on handshake.
    if "pymysql" in driver and _has_non_latin_chars(password):
        query = dict(parsed.query or {})
        query.setdefault("use_pure", "true")
        parsed = parsed.set(drivername="mysql+mysqlconnector", query=query)

    # mysqlconnector pure-python mode gives clearer/stabler errors on some Windows hosts.
    if "mysql+mysqlconnector" in (parsed.drivername or "").lower():
        query = dict(parsed.query or {})
        query.setdefault("use_pure", "true")
        parsed = parsed.set(query=query)

    return parsed.render_as_string(hide_password=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize SQLAlchemy DATABASE_URL for deployment.")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    print(normalize_database_url(args.database_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
