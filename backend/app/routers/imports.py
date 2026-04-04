import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    ROLE_ADMIN,
    CurrentUser,
    require_roles,
)
from app.db.session import get_db
from app.models.import_batch import ImportBatch, ImportType
from app.models.import_issue import ImportIssue
from app.schemas.imports import (
    ImportBatchOut,
    ImportCancelOut,
    ImportDataClearIn,
    ImportDataClearOut,
    ImportDataRestoreOut,
    ImportIssueListOut,
    ImportIssueOut,
    ImportListOut,
    ImportStartOut,
)
from app.services.import_service import (
    build_case_cost_backup,
    clear_case_cost_data,
    enqueue_case_home_basic_import,
    enqueue_case_home_filtered_import,
    enqueue_import,
    get_import_queue_depth,
    request_cancel_import_batch,
    restore_case_cost_data_from_backup_bytes,
)

router = APIRouter(prefix="/imports", tags=["imports"])


def _validate_upload_file(
    file: UploadFile,
    max_upload_mb: int,
    field_name: str,
    allowed_extensions: tuple[str, ...],
) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail=f"{field_name} 文件名为空。")
    if not file.filename.lower().endswith(allowed_extensions):
        ext_text = "/".join(allowed_extensions)
        raise HTTPException(status_code=400, detail=f"{field_name} 仅支持 {ext_text}。")
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)
    if size_bytes > max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 超过大小限制 {max_upload_mb}MB。",
        )


@router.post("/start", response_model=ImportStartOut)
def import_start(
    import_type: ImportType,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    settings = get_settings()
    if import_type == ImportType.CASE_HOME_FILTERED:
        raise HTTPException(
            status_code=400,
            detail="CASE_HOME_FILTERED 请使用 /imports/case-home/start 接口。",
        )
    _validate_upload_file(file, settings.max_upload_mb, "导入文件", (".xlsx", ".xls", ".csv"))
    if get_import_queue_depth(db) >= settings.import_queue_limit:
        raise HTTPException(status_code=429, detail="导入队列已满，请稍后再试。")

    batch = enqueue_import(db, file, import_type, requested_by=_.user_id)
    return ImportStartOut(
        message="Import task queued.",
        batch=ImportBatchOut.model_validate(batch, from_attributes=True),
    )


@router.post("/case-home/start", response_model=ImportStartOut)
def case_home_import_start(
    source_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    settings = get_settings()
    _validate_upload_file(source_file, settings.max_upload_mb, "病案首页源文件", (".xlsx", ".xls", ".csv"))
    if get_import_queue_depth(db) >= settings.import_queue_limit:
        raise HTTPException(status_code=429, detail="导入队列已满，请稍后再试。")

    batch = enqueue_case_home_basic_import(db, source_file, requested_by=_.user_id)
    return ImportStartOut(
        message="Case-home basic import queued.",
        batch=ImportBatchOut.model_validate(batch, from_attributes=True),
    )


@router.post("/case-home-filter/start", response_model=ImportStartOut)
def case_home_filtered_import_start_compat(
    source_file: UploadFile = File(...),
    filter_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    settings = get_settings()
    _validate_upload_file(source_file, settings.max_upload_mb, "病案首页源文件", (".xlsx", ".xls", ".csv"))
    if filter_file:
        _validate_upload_file(filter_file, settings.max_upload_mb, "筛选文件", (".xlsx", ".xls", ".csv"))
    if get_import_queue_depth(db) >= settings.import_queue_limit:
        raise HTTPException(status_code=429, detail="导入队列已满，请稍后再试。")

    batch = enqueue_case_home_filtered_import(db, source_file, filter_file, requested_by=_.user_id)
    return ImportStartOut(
        message="Case-home basic import queued.",
        batch=ImportBatchOut.model_validate(batch, from_attributes=True),
    )


@router.get("/backup/case-cost.xlsx")
def backup_case_cost(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    filename, content = build_case_cost_backup(db)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/clear/case-cost", response_model=ImportDataClearOut)
def clear_case_cost(
    payload: ImportDataClearIn,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    if payload.confirm_text.strip().upper() != "CLEAR_CASE_COST_DATA":
        raise HTTPException(status_code=400, detail="confirm_text mismatch")
    result = clear_case_cost_data(db)
    return ImportDataClearOut(message="Case and cost import data cleared.", **result)


@router.post("/restore/case-cost", response_model=ImportDataRestoreOut)
def restore_case_cost(
    confirm_text: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    settings = get_settings()
    if confirm_text.strip().upper() != "CLEAR_CASE_COST_DATA":
        raise HTTPException(status_code=400, detail="confirm_text mismatch")
    _validate_upload_file(file, settings.max_upload_mb, "恢复文件", (".xlsx", ".xls"))
    content = file.file.read()
    try:
        result = restore_case_cost_data_from_backup_bytes(db, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ImportDataRestoreOut(message="Case and cost data restored from backup.", **result)


@router.get("", response_model=ImportListOut)
def import_list(
    db: Session = Depends(get_db),
    limit: int = 20,
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    stmt = select(ImportBatch).order_by(desc(ImportBatch.id)).limit(limit)
    items = db.execute(stmt).scalars().all()
    return ImportListOut(
        items=[ImportBatchOut.model_validate(item, from_attributes=True) for item in items]
    )


@router.get("/{batch_id}", response_model=ImportBatchOut)
def import_batch_detail(
    batch_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    batch = db.execute(select(ImportBatch).where(ImportBatch.batch_id == batch_id)).scalars().first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return ImportBatchOut.model_validate(batch, from_attributes=True)


@router.post("/{batch_id}/cancel", response_model=ImportCancelOut)
def cancel_import_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    try:
        batch = request_cancel_import_batch(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ImportCancelOut(
        message="Import cancel request accepted.",
        batch=ImportBatchOut.model_validate(batch, from_attributes=True),
    )


@router.get("/{batch_id}/issues", response_model=ImportIssueListOut)
def import_issue_list(
    batch_id: str,
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
    severity: str | None = None,
    error_code: str | None = None,
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    page = max(page, 1)
    page_size = max(min(page_size, 500), 1)

    conditions = [ImportIssue.batch_id == batch_id]
    if severity:
        conditions.append(ImportIssue.severity == severity.upper())
    if error_code:
        conditions.append(ImportIssue.error_code == error_code.upper())

    total = (
        db.execute(select(func.count()).select_from(ImportIssue).where(and_(*conditions))).scalar_one()
    )
    stmt = (
        select(ImportIssue)
        .where(and_(*conditions))
        .order_by(ImportIssue.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(stmt).scalars().all()
    return ImportIssueListOut(
        total=int(total),
        page=page,
        page_size=page_size,
        items=[ImportIssueOut.model_validate(item, from_attributes=True) for item in items],
    )


@router.get("/{batch_id}/issues.csv")
def import_issue_csv(
    batch_id: str,
    db: Session = Depends(get_db),
    severity: str | None = None,
    error_code: str | None = None,
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    conditions = [ImportIssue.batch_id == batch_id]
    if severity:
        conditions.append(ImportIssue.severity == severity.upper())
    if error_code:
        conditions.append(ImportIssue.error_code == error_code.upper())

    stmt = select(ImportIssue).where(ImportIssue.batch_id == batch_id).order_by(ImportIssue.id.asc())
    if len(conditions) > 1:
        stmt = select(ImportIssue).where(and_(*conditions)).order_by(ImportIssue.id.asc())
    items = db.execute(stmt).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["batch_id", "row_no", "field_name", "error_code", "severity", "message"])
    for item in items:
        writer.writerow(
            [
                item.batch_id,
                item.row_no,
                item.field_name or "",
                item.error_code,
                item.severity,
                item.message,
            ]
        )
    content = output.getvalue()
    output.close()

    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="issues_{batch_id}.csv"'},
    )


@router.get("/{batch_id}/issues.xlsx")
def import_issue_xlsx(
    batch_id: str,
    db: Session = Depends(get_db),
    severity: str | None = None,
    error_code: str | None = None,
    _: CurrentUser = Depends(require_roles(ROLE_ADMIN)),
):
    conditions = [ImportIssue.batch_id == batch_id]
    if severity:
        conditions.append(ImportIssue.severity == severity.upper())
    if error_code:
        conditions.append(ImportIssue.error_code == error_code.upper())

    stmt = select(ImportIssue).where(and_(*conditions)).order_by(ImportIssue.id.asc())
    items = db.execute(stmt).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "issues"
    ws.append(["batch_id", "row_no", "field_name", "error_code", "severity", "message", "created_at"])
    for item in items:
        ws.append(
            [
                item.batch_id,
                item.row_no,
                item.field_name or "",
                item.error_code,
                item.severity,
                item.message,
                item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="issues_{batch_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx"'
            )
        },
    )
