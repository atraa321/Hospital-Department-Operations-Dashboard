from datetime import datetime

from pydantic import BaseModel


class ImportBatchOut(BaseModel):
    batch_id: str
    import_type: str
    source_filename: str
    status: str
    row_count: int
    column_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ImportStartOut(BaseModel):
    message: str
    batch: ImportBatchOut


class ImportListOut(BaseModel):
    items: list[ImportBatchOut]


class ImportIssueOut(BaseModel):
    id: int
    row_no: int
    field_name: str | None
    error_code: str
    severity: str
    message: str
    created_at: datetime


class ImportIssueListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ImportIssueOut]


class ImportDataClearIn(BaseModel):
    confirm_text: str


class ImportDataClearOut(BaseModel):
    message: str
    deleted_case_info: int
    deleted_cost_detail: int
    deleted_orphan_fee_action: int
    deleted_import_batch: int
    deleted_import_issue: int
    deleted_upload_files: int


class ImportDataRestoreOut(BaseModel):
    message: str
    deleted_case_info: int
    deleted_cost_detail: int
    deleted_orphan_fee_action: int
    deleted_import_batch: int
    deleted_import_issue: int
    deleted_upload_files: int
    restored_case_info: int
    restored_cost_detail: int
    restored_orphan_fee_action: int
    restored_import_batch: int
    restored_import_issue: int
