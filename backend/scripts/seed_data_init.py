from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from fastapi import UploadFile

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Ensure pydantic settings loads backend/.env rather than caller working directory.
os.chdir(BACKEND_ROOT)

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.import_batch import BatchStatus, ImportType
from app.services.import_service import start_case_home_basic_import, start_import


def _pick_first(seed_dir: Path, patterns: tuple[str, ...]) -> Path | None:
    for pattern in patterns:
        matches = sorted(seed_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def _run_single_import(db, file_path: Path, import_type: ImportType) -> None:
    with file_path.open("rb") as fp:
        upload_file = UploadFile(filename=file_path.name, file=fp)
        batch = start_import(db, upload_file, import_type)
    if batch.status != BatchStatus.SUCCESS.value:
        raise RuntimeError(f"{import_type.value} import failed: {batch.error_message or 'unknown error'}")
    print(f"[OK] {import_type.value}: {file_path.name} (rows={batch.row_count})")


def _run_case_home_basic_import(db, source_file: Path) -> None:
    with source_file.open("rb") as source_fp:
        source_upload = UploadFile(filename=source_file.name, file=source_fp)
        batch = start_case_home_basic_import(db, source_upload)
    if batch.status != BatchStatus.SUCCESS.value:
        raise RuntimeError(f"CASE_HOME_FILTERED import failed: {batch.error_message or 'unknown error'}")
    print(f"[OK] CASE_HOME_FILTERED: {source_file.name} (rows={batch.row_count})")


def seed_from_directory(seed_dir: Path) -> None:
    if not seed_dir.exists():
        raise FileNotFoundError(f"seed directory not found: {seed_dir}")

    dip_file = _pick_first(seed_dir, ("*DIP*分组目录库*.xlsx", "*DIP*.xlsx", "*dip*.xlsx"))
    icd10_file = _pick_first(seed_dir, ("*ICD10*.xlsx", "*icd10*.xlsx"))
    icd9_file = _pick_first(seed_dir, ("*ICD9*.xlsx", "*icd9*.xlsx"))
    case_source = _pick_first(
        seed_dir,
        ("*病案信息*.xlsx", "*病案信息*.csv", "*病案*.xlsx", "*case*info*.xlsx"),
    )
    cost_detail = _pick_first(
        seed_dir,
        ("*费用清单*.csv", "*费用明细*.csv", "*cost*detail*.csv", "*费用清单*.xlsx", "*费用明细*.xlsx"),
    )

    candidates = [dip_file, icd10_file, icd9_file, case_source, cost_detail]
    if not any(candidates):
        raise RuntimeError(f"no recognizable seed data files found in {seed_dir}")

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if dip_file:
            _run_single_import(db, dip_file, ImportType.DIP_DICT)
        else:
            print("[SKIP] DIP_DICT file not found")

        if icd10_file:
            _run_single_import(db, icd10_file, ImportType.ICD10_DICT)
        else:
            print("[SKIP] ICD10_DICT file not found")

        if icd9_file:
            _run_single_import(db, icd9_file, ImportType.ICD9_DICT)
        else:
            print("[SKIP] ICD9_DICT file not found")

        if case_source:
            _run_case_home_basic_import(db, case_source)
        else:
            print("[SKIP] CASE_HOME_FILTERED source file not found")

        if cost_detail:
            _run_single_import(db, cost_detail, ImportType.COST_DETAIL)
        else:
            print("[SKIP] COST_DETAIL file not found")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize base import data from a seed directory.")
    parser.add_argument("--seed-dir", required=True, help="Directory with initialization files.")
    args = parser.parse_args()
    seed_from_directory(Path(args.seed_dir).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
