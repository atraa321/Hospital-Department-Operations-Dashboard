from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import io
from pathlib import Path
import re
from uuid import uuid4

import pandas as pd
from fastapi import UploadFile
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.case_info import CaseInfo
from app.models.dip_catalog import DipCatalog
from app.models.cost_detail import CostDetail
from app.models.icd10_map import Icd10Map
from app.models.icd9_map import Icd9Map
from app.models.import_batch import BatchStatus, ImportBatch, ImportType
from app.models.import_issue import ImportIssue
from app.models.orphan_fee_action import OrphanFeeAction
from app.utils.cost_classifier import classify_cost_group


@dataclass
class ValidationIssue:
    row_no: int
    error_code: str
    message: str
    field_name: str | None = None
    severity: str = "ERROR"


CASE_COLS = {
    "doctor_name": "医师",
    "dept_code": "科室编号",
    "dept_name": "出院科室",
    "patient_name": "患者姓名",
    "admission_dept": "入院科室",
    "discharge_date": "出院日期",
    "admission_date": "入院日期",
    "patient_id": "住院号",
    "diagnosis_type": "诊断类型",
    "main_diagnosis_code": "诊断ICD",
    "main_diagnosis_name": "诊断名称",
    "icd_code": "icd",
    "icd3_code": "icd3",
    "surgery_code": "手术icd",
    "surgery_name": "手术名称",
}

CASE_HOME_REQUIRED_COLS = {
    "patient_id": "住院号",
}

CASE_HOME_OPTIONAL_COL_ALIASES = {
    "patient_name": ("姓名", "患者姓名"),
    "gender": ("性别",),
    "birth_date": ("出生日期", "出生年月日", "出生年月"),
    "age": ("年龄",),
    "marital_status": ("婚姻状况", "婚姻状态", "婚姻"),
    "occupation": ("职业",),
    "current_address": ("现住址", "现地址", "住址"),
}

COST_DETAIL_COLS = {
    "item_name": "项目名称",
    "quantity": "收费数量",
    "unit_price": "收费标准",
    "amount": "收费额",
    "item_code": "收费项目编码",
    "unit": "计费单位",
    "dept_name": "收费科室",
    "patient_id": "住院号",
    "patient_name": "收费对象",
    "patient_type": "brlx",
    "cost_category": "费用类别",
}
OPTIONAL_COST_DETAIL_COL_KEYS = {"dept_name"}
COST_DETAIL_REQUIRED_COLS = {
    key: value for key, value in COST_DETAIL_COLS.items() if key not in OPTIONAL_COST_DETAIL_COL_KEYS
}

COST_SUMMARY_COLS = {
    "patient_id": "住院号",
    "total_cost": "总花费",
}

KNOWN_COST_CATEGORIES = {
    "西药费",
    "成药费",
    "草药费",
    "材料费",
    "检查费",
    "CT费",
    "心电图",
    "彩超费",
    "B超费",
    "放射费",
    "胃镜费",
    "化验费",
    "检验费",
    "治疗费",
    "理疗费",
    "换药费",
    "注射费",
    "处置费",
    "手术费",
    "麻醉费",
    "护理费",
    "床位费",
    "诊查费",
    "输氧费",
    "输血费",
}

ICD_PATTERN = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,6})?$", re.IGNORECASE)
CLEAR_IMPORT_TYPES = (
    ImportType.CASE_INFO.value,
    ImportType.CASE_HOME_FILTERED.value,
    ImportType.COST_DETAIL.value,
    ImportType.COST_SUMMARY.value,
)
RESTORE_REQUIRED_SHEETS = ("case_info", "cost_detail", "import_batch", "import_issue")
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")


def _save_upload_file_for_batch(
    upload_file: UploadFile,
    import_type: ImportType,
    batch_id: str,
    file_tag: str | None = None,
) -> str:
    settings = get_settings()
    day_part = datetime.now().strftime("%Y%m%d")
    target_dir = Path(settings.upload_dir).joinpath(day_part, import_type.value.lower())
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = upload_file.filename or "unknown.xlsx"
    prefix = f"{batch_id}_{file_tag}_" if file_tag else f"{batch_id}_"
    target_path = target_dir / f"{prefix}{safe_name}"

    with target_path.open("wb") as fp:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            fp.write(chunk)

    upload_file.file.seek(0)
    return str(target_path)


def _save_upload_file(upload_file: UploadFile, import_type: ImportType) -> tuple[str, str]:
    batch_id = str(uuid4())
    target_path = _save_upload_file_for_batch(upload_file, import_type, batch_id)
    return batch_id, str(target_path)


def _load_csv(
    source,
    dtype: type | str | None = None,
    header: int | list[int] | None | str = "infer",
) -> pd.DataFrame:
    last_decode_error: UnicodeDecodeError | None = None
    for encoding in CSV_ENCODINGS:
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            return pd.read_csv(source, dtype=dtype, encoding=encoding, header=header)
        except UnicodeDecodeError as exc:
            last_decode_error = exc
            continue
    if last_decode_error:
        raise last_decode_error
    if hasattr(source, "seek"):
        source.seek(0)
    return pd.read_csv(source, dtype=dtype, header=header)


def _load_table_by_name(
    source,
    filename: str,
    dtype: type | str | None = None,
    header: int | list[int] | None | str = "infer",
) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix in (".xlsx", ".xls"):
        if hasattr(source, "seek"):
            source.seek(0)
        excel_header = 0 if header == "infer" else header
        return pd.read_excel(source, dtype=dtype, header=excel_header)
    if suffix == ".csv":
        return _load_csv(source, dtype=dtype, header=header)
    raise ValueError(f"不支持的文件类型: {suffix or '(empty)'}")


def _load_table(
    file_path: str,
    dtype: type | str | None = None,
    header: int | list[int] | None | str = "infer",
) -> pd.DataFrame:
    return _load_table_by_name(file_path, Path(file_path).name, dtype=dtype, header=header)


def _load_upload_table(
    upload_file: UploadFile,
    dtype: type | str | None = None,
    header: int | list[int] | None | str = "infer",
) -> pd.DataFrame:
    filename = upload_file.filename or ""
    if not filename:
        raise ValueError("上传文件名为空，无法识别文件类型。")
    return _load_table_by_name(upload_file.file, filename, dtype=dtype, header=header)


def _check_required_columns(df: pd.DataFrame, expected: dict[str, str]) -> list[str]:
    missing = [cn for cn in expected.values() if cn not in df.columns]
    return missing


def _normalize_case_info_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}

    # Common alias from external exports.
    if "科室编号" not in df.columns:
        if "科室编码" in df.columns:
            rename_map["科室编码"] = "科室编号"
        elif "科室代码" in df.columns:
            rename_map["科室代码"] = "科室编号"

    # Some exports contain duplicated 患者姓名 columns:
    # first is doctor full name, second is masked patient name.
    if "医师" not in df.columns and "患者姓名" in df.columns and "患者姓名.1" in df.columns:
        rename_map["患者姓名"] = "医师"
        rename_map["患者姓名.1"] = "患者姓名"
    elif "医师" not in df.columns and "主治医师" in df.columns:
        rename_map["主治医师"] = "医师"

    if not rename_map:
        return df
    return df.rename(columns=rename_map)


def _apply_headerless_fallback(
    df: pd.DataFrame,
    expected: dict[str, str],
    load_headerless_df,
) -> pd.DataFrame:
    expected_cols = list(expected.values())
    missing = _check_required_columns(df, expected)
    if not missing:
        return df
    if len(missing) != len(expected_cols):
        return df

    try:
        fallback_df = load_headerless_df()
    except Exception:  # noqa: BLE001
        return df

    if fallback_df.shape[1] < len(expected_cols):
        return df

    aligned = fallback_df.iloc[:, : len(expected_cols)].copy()
    aligned.columns = expected_cols
    return aligned


def _build_cost_summary_headerless_df(file_path: str) -> pd.DataFrame:
    raw_df = _load_table(file_path, header=None)
    expected_cols = list(COST_SUMMARY_COLS.values())
    if raw_df.shape[1] < 2:
        return raw_df

    total_idx = 1
    if raw_df.shape[1] >= 3:
        col1_numeric_ratio = pd.to_numeric(raw_df.iloc[:, 1], errors="coerce").notna().mean()
        col2_numeric_ratio = pd.to_numeric(raw_df.iloc[:, 2], errors="coerce").notna().mean()
        if col2_numeric_ratio > col1_numeric_ratio:
            total_idx = 2

    aligned = raw_df.iloc[:, [0, total_idx]].copy()
    aligned.columns = expected_cols
    return aligned


def _record_issues(db: Session, batch_id: str, issues: list[ValidationIssue]) -> None:
    if not issues:
        return
    db.add_all(
        [
            ImportIssue(
                batch_id=batch_id,
                row_no=item.row_no,
                field_name=item.field_name,
                error_code=item.error_code,
                severity=item.severity,
                message=item.message,
            )
            for item in issues
        ]
    )
    db.commit()


def _upsert_case_infos(db: Session, records: list[dict], batch_id: str) -> None:
    if not records:
        return
    patient_ids = [str(item["patient_id"]) for item in records]
    exists = db.execute(select(CaseInfo).where(CaseInfo.patient_id.in_(patient_ids))).scalars().all()
    exists_map = {item.patient_id: item for item in exists}

    for row in records:
        pid = str(row["patient_id"])
        obj = exists_map.get(pid)
        if not obj:
            obj = CaseInfo(patient_id=pid)
            db.add(obj)
        for field_name in (
            "patient_name",
            "gender",
            "birth_date",
            "age",
            "marital_status",
            "occupation",
            "current_address",
            "doctor_name",
            "dept_code",
            "dept_name",
            "admission_dept",
            "admission_date",
            "discharge_date",
            "los",
            "diagnosis_type",
            "main_diagnosis_code",
            "main_diagnosis_name",
            "icd_code",
            "icd3_code",
            "surgery_code",
            "surgery_name",
        ):
            if field_name in row:
                setattr(obj, field_name, row.get(field_name))
        obj.import_batch = batch_id
    db.commit()


def _import_case_info(db: Session, df: pd.DataFrame, batch_id: str) -> tuple[int, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    valid_records: list[dict] = []

    for idx, row in df.iterrows():
        row_no = idx + 2
        patient_id = str(row.get(CASE_COLS["patient_id"], "")).strip()
        if not patient_id or patient_id.lower() == "nan":
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V001",
                    field_name="住院号",
                    message="住院号为空，记录被拒绝。",
                )
            )
            continue

        adm = pd.to_datetime(row.get(CASE_COLS["admission_date"]), errors="coerce")
        dis = pd.to_datetime(row.get(CASE_COLS["discharge_date"]), errors="coerce")
        if pd.isna(adm) or pd.isna(dis):
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V002",
                    field_name="入院日期/出院日期",
                    message="日期格式非法，记录被拒绝。",
                )
            )
            continue
        if dis < adm:
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V003",
                    field_name="出院日期",
                    message="出院日期早于入院日期，记录被拒绝。",
                )
            )
            continue

        main_diag_code = _to_str_or_none(row.get(CASE_COLS["main_diagnosis_code"]))
        icd_code = _to_str_or_none(row.get(CASE_COLS["icd_code"]))
        if main_diag_code and not _is_valid_icd(main_diag_code):
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V006",
                    field_name="诊断ICD",
                    severity="WARN",
                    message=f"诊断ICD({main_diag_code}) 格式疑似异常，请核对编码字典。",
                )
            )
        if icd_code and not _is_valid_icd(icd_code):
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V006",
                    field_name="icd",
                    severity="WARN",
                    message=f"icd({icd_code}) 格式疑似异常，请核对编码字典。",
                )
            )

        valid_records.append(
            {
                "patient_id": patient_id,
                "patient_name": _to_str_or_none(row.get(CASE_COLS["patient_name"])),
                "doctor_name": _to_str_or_none(row.get(CASE_COLS["doctor_name"])),
                "dept_code": _to_str_or_none(row.get(CASE_COLS["dept_code"])),
                "dept_name": _to_str_or_none(row.get(CASE_COLS["dept_name"])),
                "admission_dept": _to_str_or_none(row.get(CASE_COLS["admission_dept"])),
                "admission_date": adm.date(),
                "discharge_date": dis.date(),
                "los": int((dis - adm).days + 1),
                "diagnosis_type": _to_str_or_none(row.get(CASE_COLS["diagnosis_type"])),
                "main_diagnosis_code": main_diag_code,
                "main_diagnosis_name": _to_str_or_none(row.get(CASE_COLS["main_diagnosis_name"])),
                "icd_code": icd_code,
                "icd3_code": _to_str_or_none(row.get(CASE_COLS["icd3_code"])),
                "surgery_code": _to_str_or_none(row.get(CASE_COLS["surgery_code"])),
                "surgery_name": _to_str_or_none(row.get(CASE_COLS["surgery_name"])),
            }
        )

    _upsert_case_infos(db, valid_records, batch_id)
    _record_issues(db, batch_id, issues)
    return len(valid_records), issues


def _to_str_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return None
    return float(num)


def _is_valid_icd(value: str | None) -> bool:
    if not value:
        return False
    return bool(ICD_PATTERN.match(value.strip()))


def _normalize_patient_id(value: object) -> str | None:
    text = _to_str_or_none(value)
    if not text:
        return None
    normalized = text.replace("\u3000", "").strip()
    if normalized.endswith(".0"):
        normalized = normalized[:-2]
    if normalized.isdigit():
        normalized = str(int(normalized))
    return normalized or None


def _resolve_case_home_optional_columns(df: pd.DataFrame) -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    for field_name, aliases in CASE_HOME_OPTIONAL_COL_ALIASES.items():
        selected = None
        for column_name in aliases:
            if column_name in df.columns:
                selected = column_name
                break
        resolved[field_name] = selected
    return resolved


def _import_case_home_basic(
    db: Session,
    source_df: pd.DataFrame,
    batch_id: str,
) -> tuple[int, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    valid_records: list[dict] = []
    optional_columns = _resolve_case_home_optional_columns(source_df)

    for idx, row in source_df.iterrows():
        row_no = idx + 2
        patient_id = _normalize_patient_id(row.get(CASE_HOME_REQUIRED_COLS["patient_id"]))
        if not patient_id:
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V001",
                    field_name="住院号",
                    message="住院号为空，记录被拒绝。",
                )
            )
            continue

        birth_date_col = optional_columns["birth_date"]
        age_col = optional_columns["age"]
        birth_date_raw = row.get(birth_date_col) if birth_date_col else None
        birth_date_ts = pd.to_datetime(birth_date_raw, errors="coerce")
        birth_date = birth_date_ts.date() if not pd.isna(birth_date_ts) else None
        age_value = _to_float(row.get(age_col)) if age_col else None
        age = int(age_value) if age_value is not None else None

        valid_records.append(
            {
                "patient_id": patient_id,
                "patient_name": _to_str_or_none(
                    row.get(optional_columns["patient_name"]) if optional_columns["patient_name"] else None
                ),
                "gender": _to_str_or_none(
                    row.get(optional_columns["gender"]) if optional_columns["gender"] else None
                ),
                "birth_date": birth_date,
                "age": age,
                "marital_status": _to_str_or_none(
                    row.get(optional_columns["marital_status"]) if optional_columns["marital_status"] else None
                ),
                "occupation": _to_str_or_none(
                    row.get(optional_columns["occupation"]) if optional_columns["occupation"] else None
                ),
                "current_address": _to_str_or_none(
                    row.get(optional_columns["current_address"]) if optional_columns["current_address"] else None
                ),
            }
        )

    _upsert_case_infos(db, valid_records, batch_id)
    _record_issues(db, batch_id, issues)
    return len(valid_records), issues


def _detail_key(patient_id: str, item_name: str | None, unit_price: float) -> tuple[str, str, float]:
    return (patient_id, (item_name or "").strip(), round(float(unit_price), 4))


def _import_cost_detail(
    db: Session, df: pd.DataFrame, batch_id: str
) -> tuple[int, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    valid_rows: list[dict] = []
    patient_ids: set[str] = set()

    for idx, row in df.iterrows():
        row_no = idx + 2
        patient_id = _to_str_or_none(row.get(COST_DETAIL_COLS["patient_id"]))
        if not patient_id:
            issues.append(ValidationIssue(row_no, "V001", "住院号为空，记录被拒绝。", "住院号"))
            continue

        quantity = _to_float(row.get(COST_DETAIL_COLS["quantity"]))
        unit_price = _to_float(row.get(COST_DETAIL_COLS["unit_price"]))
        amount = _to_float(row.get(COST_DETAIL_COLS["amount"]))
        if quantity is None or unit_price is None or amount is None:
            issues.append(ValidationIssue(row_no, "V004", "金额或数量字段非数值，记录被拒绝。", "收费数量/收费标准/收费额"))
            continue

        raw_category = _to_str_or_none(row.get(COST_DETAIL_COLS["cost_category"]))
        cost_group = classify_cost_group(raw_category)
        if raw_category and raw_category not in KNOWN_COST_CATEGORIES:
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V009",
                    field_name="费用类别",
                    severity="WARN",
                    message=f"费用类别 {raw_category} 未在标准字典中定义，已归入其他费用。",
                )
            )

        item = {
            "patient_id": patient_id,
            "patient_name": _to_str_or_none(row.get(COST_DETAIL_COLS["patient_name"])),
            "item_name": _to_str_or_none(row.get(COST_DETAIL_COLS["item_name"])),
            "item_code": _to_str_or_none(row.get(COST_DETAIL_COLS["item_code"])),
            "quantity": quantity,
            "unit_price": unit_price,
            "amount": amount,
            "unit": _to_str_or_none(row.get(COST_DETAIL_COLS["unit"])),
            "dept_name": _to_str_or_none(row.get(COST_DETAIL_COLS["dept_name"])),
            "cost_category": raw_category,
            "cost_group": cost_group,
            "patient_type": _to_str_or_none(row.get(COST_DETAIL_COLS["patient_type"])),
            "import_batch": batch_id,
            "source_row_no": row_no,
        }
        valid_rows.append(item)

    # 费用清单只允许导入病案主表中已存在的住院号（病案出院病人.xlsx）
    if valid_rows:
        candidate_patient_ids = sorted({str(item["patient_id"]) for item in valid_rows})
        case_patient_ids = set(
            db.execute(select(CaseInfo.patient_id).where(CaseInfo.patient_id.in_(candidate_patient_ids)))
            .scalars()
            .all()
        )

        filtered_rows: list[dict] = []
        for item in valid_rows:
            if item["patient_id"] not in case_patient_ids:
                issues.append(
                    ValidationIssue(
                        row_no=int(item["source_row_no"]),
                        error_code="V010",
                        field_name="住院号",
                        severity="WARN",
                        message=f"费用明细住院号 {item['patient_id']} 在病案主表中不存在，记录被跳过。",
                    )
                )
                continue
            filtered_rows.append(item)
            patient_ids.add(str(item["patient_id"]))
        valid_rows = filtered_rows

    if valid_rows:
        existing_rows = (
            db.execute(
                select(
                    CostDetail.patient_id,
                    CostDetail.item_name,
                    CostDetail.unit_price,
                    CostDetail.quantity,
                    CostDetail.amount,
                    CostDetail.import_batch,
                ).where(CostDetail.patient_id.in_(list(patient_ids)))
            )
            .all()
        )
        existing_map: dict[tuple[str, str, float], list[dict]] = {}
        for row in existing_rows:
            key = _detail_key(row.patient_id, row.item_name, float(row.unit_price or 0))
            existing_map.setdefault(key, []).append(
                {
                    "quantity": float(row.quantity or 0),
                    "amount": float(row.amount or 0),
                    "import_batch": row.import_batch,
                }
            )

        v008_count = 0
        for item in valid_rows:
            key = _detail_key(item["patient_id"], item["item_name"], item["unit_price"])
            previous = existing_map.get(key, [])
            if not previous:
                continue
            same_payload = any(
                abs(prev["quantity"] - float(item["quantity"])) <= 0.0001
                and abs(prev["amount"] - float(item["amount"])) <= 0.01
                for prev in previous
            )
            if not same_payload and v008_count < 100:
                issues.append(
                    ValidationIssue(
                        row_no=int(item["source_row_no"]),
                        error_code="V008",
                        field_name="住院号+项目名称+收费标准",
                        severity="WARN",
                        message=(
                            "检测到跨批次同明细键金额/数量不一致，"
                            "系统保留历史记录并按最新记录参与汇总。"
                        ),
                    )
                )
                v008_count += 1

        detail_df = pd.DataFrame(valid_rows)
        dup = detail_df.duplicated(subset=["patient_id", "item_name", "unit_price"], keep=False)
        if bool(dup.any()):
            dup_rows = detail_df[dup]
            for _, item in dup_rows.head(100).iterrows():
                issues.append(
                    ValidationIssue(
                        row_no=int(item.get("source_row_no", 0) or 0),
                        error_code="V007",
                        field_name="住院号+项目名称+收费标准",
                        severity="WARN",
                        message=(
                            "检测到明细组合重复，当前按原始记录入库，"
                            "建议结合业务规则核对是否重复收费。"
                        ),
                    )
                )

        to_insert = []
        for item in valid_rows:
            payload = dict(item)
            payload.pop("source_row_no", None)
            to_insert.append(CostDetail(**payload))
        db.add_all(to_insert)
        db.commit()

        _recalc_case_costs(db, list(patient_ids), batch_id, issues)

    _record_issues(db, batch_id, issues)
    return len(valid_rows), issues


def _recalc_case_costs(
    db: Session, patient_ids: list[str], batch_id: str, issues: list[ValidationIssue]
) -> None:
    if not patient_ids:
        return

    details = db.execute(select(CostDetail).where(CostDetail.patient_id.in_(patient_ids))).scalars().all()
    latest_by_key: dict[tuple[str, str, float], CostDetail] = {}
    for row in details:
        key = _detail_key(row.patient_id, row.item_name, float(row.unit_price or 0))
        latest = latest_by_key.get(key)
        if latest is None or int(row.id) > int(latest.id):
            latest_by_key[key] = row

    grouped: dict[str, dict[str, float]] = {}
    for row in latest_by_key.values():
        pid = row.patient_id
        if pid not in grouped:
            grouped[pid] = {
                "药品费": 0.0,
                "草药费": 0.0,
                "材料费": 0.0,
                "检查费": 0.0,
                "治疗费": 0.0,
                "手术费": 0.0,
                "护理费": 0.0,
                "服务费": 0.0,
                "其他费用": 0.0,
                "总费用": 0.0,
            }
        amount = float(row.amount or 0)
        grouped[pid]["总费用"] += amount
        grouped[pid][row.cost_group or "其他费用"] += amount

    cases = db.execute(select(CaseInfo).where(CaseInfo.patient_id.in_(patient_ids))).scalars().all()
    case_map = {item.patient_id: item for item in cases}
    for idx, pid in enumerate(patient_ids):
        case = case_map.get(pid)
        if not case:
            issues.append(
                ValidationIssue(
                    row_no=idx + 1,
                    error_code="V010",
                    field_name="住院号",
                    severity="WARN",
                    message=f"费用明细住院号 {pid} 在病案主表中不存在，未更新汇总。",
                )
            )
            continue
        payload = grouped.get(pid, {})
        case.total_cost = payload.get("总费用", 0.0)
        case.drug_cost = payload.get("药品费", 0.0)
        case.herb_cost = payload.get("草药费", 0.0)
        case.material_cost = payload.get("材料费", 0.0)
        case.exam_cost = payload.get("检查费", 0.0)
        case.treatment_cost = payload.get("治疗费", 0.0)
        case.surgery_cost = payload.get("手术费", 0.0)
        case.nursing_cost = payload.get("护理费", 0.0)
        case.service_cost = payload.get("服务费", 0.0)
        case.other_cost = payload.get("其他费用", 0.0)
        case.import_batch = batch_id
    db.commit()


def _import_cost_summary(
    db: Session, df: pd.DataFrame, batch_id: str
) -> tuple[int, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    updated = 0
    for idx, row in df.iterrows():
        row_no = idx + 2
        patient_id = _to_str_or_none(row.get(COST_SUMMARY_COLS["patient_id"]))
        total_cost = _to_float(row.get(COST_SUMMARY_COLS["total_cost"]))
        if not patient_id:
            issues.append(ValidationIssue(row_no, "V001", "住院号为空，记录被拒绝。", "住院号"))
            continue
        if total_cost is None:
            issues.append(
                ValidationIssue(row_no, "V004", "总花费不是有效数值，记录被拒绝。", "总花费")
            )
            continue

        case = db.execute(select(CaseInfo).where(CaseInfo.patient_id == patient_id)).scalar_one_or_none()
        if not case:
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V010",
                    field_name="住院号",
                    severity="WARN",
                    message=f"费用汇总住院号 {patient_id} 在病案主表中不存在。",
                )
            )
            continue

        case.total_cost = total_cost
        component_total = float(
            (case.drug_cost or 0)
            + (case.herb_cost or 0)
            + (case.material_cost or 0)
            + (case.exam_cost or 0)
            + (case.treatment_cost or 0)
            + (case.surgery_cost or 0)
            + (case.nursing_cost or 0)
            + (case.service_cost or 0)
            + (case.other_cost or 0)
        )
        if component_total > 0 and abs(component_total - total_cost) > 0.01:
            issues.append(
                ValidationIssue(
                    row_no=row_no,
                    error_code="V005",
                    field_name="总花费",
                    severity="WARN",
                    message=(
                        f"总花费({total_cost:.2f})与当前分项和({component_total:.2f})不一致。"
                    ),
                )
            )
        case.import_batch = batch_id
        updated += 1
    db.commit()
    _record_issues(db, batch_id, issues)
    return updated, issues


def _extract_version(file_path: str, import_type: ImportType) -> str:
    filename = Path(file_path).name
    if import_type == ImportType.DIP_DICT:
        year = re.search(r"(20\d{2})", filename)
        if year:
            return year.group(1)
    version = re.search(r"(\d+\.\d+)", filename)
    if version:
        return version.group(1)
    return datetime.now().strftime("%Y%m%d")


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in df.columns:
        if str(col).strip() in candidates:
            return str(col)
    return None


def _import_icd10_dict(
    db: Session, df: pd.DataFrame, batch_id: str, version: str
) -> tuple[int, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    source_code_col = _find_col(df, ["国临版编码"])
    source_name_col = _find_col(df, ["国临版名称"])
    target_code_col = _find_col(df, ["医保版2.0编码"])
    target_name_col = _find_col(df, ["医保版2.0名称"])
    if not source_code_col:
        raise ValueError("ICD10字典缺少必要字段: 国临版编码")

    db.execute(delete(Icd10Map).where(Icd10Map.version == version))
    rows: list[Icd10Map] = []
    for idx, row in df.iterrows():
        source_code = _to_str_or_none(row.get(source_code_col))
        if not source_code:
            issues.append(ValidationIssue(idx + 2, "V901", "ICD10源编码为空，跳过。", source_code_col, "WARN"))
            continue
        rows.append(
            Icd10Map(
                version=version,
                source_code=source_code,
                source_name=_to_str_or_none(row.get(source_name_col)) if source_name_col else None,
                target_code=_to_str_or_none(row.get(target_code_col)) if target_code_col else None,
                target_name=_to_str_or_none(row.get(target_name_col)) if target_name_col else None,
                import_batch=batch_id,
            )
        )
    if rows:
        db.add_all(rows)
    db.commit()
    return len(rows), issues


def _import_icd9_dict(
    db: Session, df: pd.DataFrame, batch_id: str, version: str
) -> tuple[int, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    source_code_col = _find_col(df, ["国临3.0手术代码"])
    source_name_col = _find_col(df, ["国临3.0手术名称"])
    target_code_col = _find_col(df, ["医保2.0手术代码"])
    target_name_col = _find_col(df, ["医保2.0手术名称"])
    if not source_code_col:
        raise ValueError("ICD9字典缺少必要字段: 国临3.0手术代码")

    db.execute(delete(Icd9Map).where(Icd9Map.version == version))
    rows: list[Icd9Map] = []
    for idx, row in df.iterrows():
        source_code = _to_str_or_none(row.get(source_code_col))
        if not source_code:
            issues.append(ValidationIssue(idx + 2, "V902", "ICD9源编码为空，跳过。", source_code_col, "WARN"))
            continue
        rows.append(
            Icd9Map(
                version=version,
                source_code=source_code,
                source_name=_to_str_or_none(row.get(source_name_col)) if source_name_col else None,
                target_code=_to_str_or_none(row.get(target_code_col)) if target_code_col else None,
                target_name=_to_str_or_none(row.get(target_name_col)) if target_name_col else None,
                import_batch=batch_id,
            )
        )
    if rows:
        db.add_all(rows)
    db.commit()
    return len(rows), issues


def _import_dip_dict(
    db: Session, df: pd.DataFrame, batch_id: str, version: str
) -> tuple[int, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    code_col = _find_col(df, ["DIP_CODE", "THIRD_DIP_CODE"])
    year_col = _find_col(df, ["`YEAR`", "YEAR"])
    weight_col = _find_col(df, ["WEIGHT_SCORE", "WEIGHT"])
    avg_fee_col = _find_col(df, ["DIP_AVG_FEE", "THIRD_DIP_COST"])
    avg_days_col = _find_col(df, ["AVG_IPT_DAYS"])
    remark_col = _find_col(df, ["REMARK"])
    if not code_col:
        raise ValueError("DIP目录缺少必要字段: DIP_CODE")

    db.execute(delete(DipCatalog).where(DipCatalog.version == version))
    rows: list[DipCatalog] = []
    for idx, row in df.iterrows():
        dip_code = _to_str_or_none(row.get(code_col))
        if not dip_code:
            issues.append(ValidationIssue(idx + 2, "V903", "DIP编码为空，跳过。", code_col, "WARN"))
            continue
        year_value = _to_float(row.get(year_col)) if year_col else None
        rows.append(
            DipCatalog(
                version=version,
                dip_code=dip_code,
                year=int(year_value) if year_value is not None else None,
                weight_score=_to_float(row.get(weight_col)) if weight_col else None,
                dip_avg_fee=_to_float(row.get(avg_fee_col)) if avg_fee_col else None,
                avg_ipt_days=_to_float(row.get(avg_days_col)) if avg_days_col else None,
                remark=_to_str_or_none(row.get(remark_col)) if remark_col else None,
                import_batch=batch_id,
            )
        )
    if rows:
        db.add_all(rows)
    db.commit()
    return len(rows), issues


def _import_dict_table(
    db: Session,
    df: pd.DataFrame,
    batch_id: str,
    import_type: ImportType,
    file_path: str,
) -> tuple[int, list[ValidationIssue]]:
    version = _extract_version(file_path, import_type)
    if import_type == ImportType.ICD10_DICT:
        return _import_icd10_dict(db, df, batch_id, version)
    if import_type == ImportType.ICD9_DICT:
        return _import_icd9_dict(db, df, batch_id, version)
    if import_type == ImportType.DIP_DICT:
        return _import_dip_dict(db, df, batch_id, version)
    return 0, []


def _run_import(
    db: Session, import_type: ImportType, file_path: str, batch_id: str
) -> tuple[int, int, int, str | None]:
    df = _load_table(file_path)

    if import_type == ImportType.CASE_INFO:
        df = _normalize_case_info_columns(df)
        df = _apply_headerless_fallback(
            df,
            CASE_COLS,
            load_headerless_df=lambda: _normalize_case_info_columns(_load_table(file_path, header=None)),
        )
        missing = _check_required_columns(df, CASE_COLS)
        if missing:
            raise ValueError(f"CASE_INFO 缺少字段: {', '.join(missing)}")
        success, issues = _import_case_info(db, df, batch_id)
    elif import_type == ImportType.COST_DETAIL:
        df = _apply_headerless_fallback(
            df,
            COST_DETAIL_REQUIRED_COLS,
            load_headerless_df=lambda: _load_table(file_path, header=None),
        )
        missing = _check_required_columns(df, COST_DETAIL_REQUIRED_COLS)
        if missing:
            raise ValueError(f"COST_DETAIL 缺少字段: {', '.join(missing)}")
        success, issues = _import_cost_detail(db, df, batch_id)
    elif import_type == ImportType.COST_SUMMARY:
        df = _apply_headerless_fallback(df, COST_SUMMARY_COLS, load_headerless_df=lambda: _build_cost_summary_headerless_df(file_path))
        missing = _check_required_columns(df, COST_SUMMARY_COLS)
        if missing:
            raise ValueError(f"COST_SUMMARY 缺少字段: {', '.join(missing)}")
        success, issues = _import_cost_summary(db, df, batch_id)
    else:
        success, issues = _import_dict_table(db, df, batch_id, import_type, file_path)
        _record_issues(db, batch_id, issues)

    rows, cols = int(df.shape[0]), int(df.shape[1])
    err_count = sum(1 for item in issues if item.severity == "ERROR")
    warn_count = sum(1 for item in issues if item.severity == "WARN")
    message = None
    if issues:
        message = f"issues: errors={err_count}, warnings={warn_count}"
    return rows, cols, success, message


def _run_case_home_basic_import(
    db: Session,
    source_file_path: str,
    batch_id: str,
) -> tuple[int, int, int, str | None]:
    source_df = _load_table(source_file_path, dtype=str)
    missing_source = _check_required_columns(source_df, CASE_HOME_REQUIRED_COLS)
    if missing_source and source_df.shape[1] > 0:
        first_column_name = str(source_df.columns[0]).strip()
        looks_headerless = bool(
            re.fullmatch(r"\d+(\.0)?", first_column_name)
            or first_column_name.lower().startswith("unnamed:")
        )
        if looks_headerless:
            source_df = _apply_headerless_fallback(
                source_df,
                CASE_HOME_REQUIRED_COLS,
                load_headerless_df=lambda: _load_table(source_file_path, dtype=str, header=None),
            )
            missing_source = _check_required_columns(source_df, CASE_HOME_REQUIRED_COLS)
    if missing_source:
        raise ValueError(f"CASE_HOME_FILTERED 源文件缺少字段: {', '.join(missing_source)}")

    success, issues = _import_case_home_basic(db, source_df, batch_id)
    rows, cols = int(source_df.shape[0]), int(source_df.shape[1])
    err_count = sum(1 for item in issues if item.severity == "ERROR")
    warn_count = sum(1 for item in issues if item.severity == "WARN")
    message = None
    if issues:
        message = f"issues: errors={err_count}, warnings={warn_count}"
    return rows, cols, success, message


def _read_table_df(db: Session, model, order_by: str = "id", where_clause=None) -> pd.DataFrame:
    columns = [column.name for column in model.__table__.columns]
    stmt = select(*[getattr(model, column) for column in columns])
    if where_clause is not None:
        stmt = stmt.where(where_clause)
    if hasattr(model, order_by):
        stmt = stmt.order_by(getattr(model, order_by).asc())
    rows = db.execute(stmt).all()
    return pd.DataFrame(rows, columns=columns)


def build_case_cost_backup(db: Session) -> tuple[str, bytes]:
    case_df = _read_table_df(db, CaseInfo, order_by="id")
    cost_df = _read_table_df(db, CostDetail, order_by="id")
    orphan_df = _read_table_df(db, OrphanFeeAction, order_by="id")

    import_batch_df = _read_table_df(
        db,
        ImportBatch,
        order_by="id",
        where_clause=ImportBatch.import_type.in_(CLEAR_IMPORT_TYPES),
    )

    issue_df = pd.DataFrame(columns=[column.name for column in ImportIssue.__table__.columns])
    if not import_batch_df.empty:
        batch_ids = [str(item) for item in import_batch_df["batch_id"].tolist()]
        issue_df = _read_table_df(
            db,
            ImportIssue,
            order_by="id",
            where_clause=ImportIssue.batch_id.in_(batch_ids),
        )

    meta_df = pd.DataFrame(
        [
            {"key": "generated_at", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"key": "case_info_rows", "value": int(case_df.shape[0])},
            {"key": "cost_detail_rows", "value": int(cost_df.shape[0])},
            {"key": "orphan_fee_action_rows", "value": int(orphan_df.shape[0])},
            {"key": "import_batch_rows", "value": int(import_batch_df.shape[0])},
            {"key": "import_issue_rows", "value": int(issue_df.shape[0])},
        ]
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        case_df.to_excel(writer, sheet_name="case_info", index=False)
        cost_df.to_excel(writer, sheet_name="cost_detail", index=False)
        orphan_df.to_excel(writer, sheet_name="orphan_fee_action", index=False)
        import_batch_df.to_excel(writer, sheet_name="import_batch", index=False)
        issue_df.to_excel(writer, sheet_name="import_issue", index=False)
        meta_df.to_excel(writer, sheet_name="meta", index=False)
    buffer.seek(0)

    filename = f"case_cost_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return filename, buffer.getvalue()


def clear_case_cost_data(db: Session) -> dict[str, int]:
    upload_paths = db.execute(
        select(ImportBatch.stored_path).where(ImportBatch.import_type.in_(CLEAR_IMPORT_TYPES))
    ).scalars().all()

    try:
        deleted_import_issue = (
            db.execute(
                delete(ImportIssue).where(
                    ImportIssue.batch_id.in_(
                        select(ImportBatch.batch_id).where(ImportBatch.import_type.in_(CLEAR_IMPORT_TYPES))
                    )
                )
            ).rowcount
            or 0
        )
        deleted_import_batch = (
            db.execute(delete(ImportBatch).where(ImportBatch.import_type.in_(CLEAR_IMPORT_TYPES))).rowcount
            or 0
        )
        deleted_orphan_fee_action = db.execute(delete(OrphanFeeAction)).rowcount or 0
        deleted_cost_detail = db.execute(delete(CostDetail)).rowcount or 0
        deleted_case_info = db.execute(delete(CaseInfo)).rowcount or 0
        db.commit()
    except Exception:
        db.rollback()
        raise

    deleted_upload_files = 0
    for item in upload_paths:
        file_path = Path(str(item))
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_upload_files += 1
        except OSError:
            continue

    return {
        "deleted_case_info": int(deleted_case_info),
        "deleted_cost_detail": int(deleted_cost_detail),
        "deleted_orphan_fee_action": int(deleted_orphan_fee_action),
        "deleted_import_batch": int(deleted_import_batch),
        "deleted_import_issue": int(deleted_import_issue),
        "deleted_upload_files": int(deleted_upload_files),
    }


def _normalize_cell_value(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            return value
    return value


def _coerce_value_for_column(column, value: object | None) -> object | None:
    if value is None:
        return None
    try:
        python_type = column.type.python_type
    except Exception:  # noqa: BLE001
        return value

    if python_type is date and isinstance(value, datetime):
        return value.date()
    if python_type is datetime and isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, datetime.min.time())
    if python_type is int and isinstance(value, float):
        return int(value)
    if python_type is float and not isinstance(value, float):
        return float(value)
    if python_type is str and not isinstance(value, str):
        return str(value)
    return value


def _rows_for_model_from_df(model, df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    model_columns = {column.name: column for column in model.__table__.columns}
    source_columns = {str(column).strip(): column for column in df.columns}
    insert_columns = [name for name in source_columns if name in model_columns and name != "id"]
    if not insert_columns:
        return []

    narrowed = df[[source_columns[name] for name in insert_columns]].copy()
    narrowed.columns = insert_columns

    rows: list[dict] = []
    for item in narrowed.to_dict(orient="records"):
        payload: dict[str, object | None] = {}
        for field, raw_value in item.items():
            normalized = _normalize_cell_value(raw_value)
            column = model_columns[field]
            if normalized is None and column.default is not None:
                continue
            if normalized is None and column.server_default is not None:
                continue
            payload[field] = _coerce_value_for_column(column, normalized)
        if payload:
            rows.append(payload)
    return rows


def _restore_table_from_df(db: Session, model, df: pd.DataFrame) -> int:
    rows = _rows_for_model_from_df(model, df)
    if not rows:
        return 0
    db.execute(insert(model), rows)
    return len(rows)


def restore_case_cost_data_from_backup_bytes(db: Session, file_bytes: bytes) -> dict[str, int]:
    if not file_bytes:
        raise ValueError("backup file is empty")

    try:
        sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("backup file parse failed") from exc

    normalized_sheets = {str(name).strip().lower(): frame for name, frame in sheets.items()}
    missing_sheets = [name for name in RESTORE_REQUIRED_SHEETS if name not in normalized_sheets]
    if missing_sheets:
        raise ValueError(f"backup missing required sheets: {', '.join(missing_sheets)}")

    deleted_result = clear_case_cost_data(db)

    case_df = normalized_sheets["case_info"]
    cost_df = normalized_sheets["cost_detail"]
    batch_df = normalized_sheets["import_batch"]
    issue_df = normalized_sheets["import_issue"]
    orphan_df = normalized_sheets.get("orphan_fee_action", pd.DataFrame())

    try:
        restored_case_info = _restore_table_from_df(db, CaseInfo, case_df)
        restored_cost_detail = _restore_table_from_df(db, CostDetail, cost_df)
        restored_orphan_fee_action = _restore_table_from_df(db, OrphanFeeAction, orphan_df)
        restored_import_batch = _restore_table_from_df(db, ImportBatch, batch_df)
        restored_import_issue = _restore_table_from_df(db, ImportIssue, issue_df)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        **deleted_result,
        "restored_case_info": int(restored_case_info),
        "restored_cost_detail": int(restored_cost_detail),
        "restored_orphan_fee_action": int(restored_orphan_fee_action),
        "restored_import_batch": int(restored_import_batch),
        "restored_import_issue": int(restored_import_issue),
    }


def start_case_home_basic_import(
    db: Session,
    source_file: UploadFile,
) -> ImportBatch:
    batch_id = str(uuid4())
    stored_path = _save_upload_file_for_batch(
        upload_file=source_file,
        import_type=ImportType.CASE_HOME_FILTERED,
        batch_id=batch_id,
        file_tag="source",
    )
    batch = ImportBatch(
        batch_id=batch_id,
        import_type=ImportType.CASE_HOME_FILTERED.value,
        source_filename=source_file.filename or "unknown.xlsx",
        stored_path=stored_path,
        status=BatchStatus.PENDING.value,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    try:
        rows, cols, success, message = _run_case_home_basic_import(
            db=db,
            source_file_path=stored_path,
            batch_id=batch_id,
        )
        batch.row_count = rows
        batch.column_count = cols
        batch.status = BatchStatus.SUCCESS.value if success > 0 else BatchStatus.FAILED.value
        batch.error_message = message
    except Exception as exc:  # noqa: BLE001
        batch.status = BatchStatus.FAILED.value
        batch.error_message = str(exc)

    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def start_case_home_filtered_import(
    db: Session,
    source_file: UploadFile,
    filter_file: UploadFile | None = None,
) -> ImportBatch:
    # Compatibility entrypoint: filter file is ignored by design.
    _ = filter_file
    return start_case_home_basic_import(db, source_file)


def start_import(db: Session, upload_file: UploadFile, import_type: ImportType) -> ImportBatch:
    batch_id, stored_path = _save_upload_file(upload_file, import_type)
    batch = ImportBatch(
        batch_id=batch_id,
        import_type=import_type.value,
        source_filename=upload_file.filename or "unknown.xlsx",
        stored_path=stored_path,
        status=BatchStatus.PENDING.value,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    try:
        rows, cols, success, message = _run_import(db, import_type, stored_path, batch_id)
        batch.row_count = rows
        batch.column_count = cols
        batch.status = BatchStatus.SUCCESS.value if success > 0 else BatchStatus.FAILED.value
        batch.error_message = message
    except Exception as exc:  # noqa: BLE001
        batch.status = BatchStatus.FAILED.value
        batch.error_message = str(exc)

    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch
