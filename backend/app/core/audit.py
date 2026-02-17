from __future__ import annotations

from starlette.requests import Request

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog


def should_audit(method: str, path: str) -> bool:
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        return True
    return path.endswith(".csv") or path.endswith(".xlsx")


def classify_action(method: str, path: str) -> str:
    if "/imports" in path:
        if path.endswith(".csv") or path.endswith(".xlsx"):
            return "EXPORT"
        return "IMPORT"
    if "/config" in path:
        return "CONFIG"
    if "/dip" in path:
        return "DIP"
    if "/alerts" in path or "/workorders" in path:
        return "WORKFLOW"
    return "ACCESS"


def write_audit_log(request: Request, status_code: int) -> None:
    method = request.method.upper()
    path = request.url.path
    if not should_audit(method, path):
        return

    db = SessionLocal()
    try:
        db.add(
            AuditLog(
                user_id=request.headers.get("x-user-id"),
                role=(request.headers.get("x-role") or "").upper() or None,
                dept_name=request.headers.get("x-dept-name"),
                action=classify_action(method, path),
                method=method,
                path=path,
                status_code=int(status_code),
                detail=request.url.query or None,
            )
        )
        db.commit()
    finally:
        db.close()
