from __future__ import annotations

from dataclasses import dataclass
import json
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, Header, HTTPException, Request

from app.core.config import get_settings


ROLE_ADMIN = "ADMIN"
ROLE_DIRECTOR = "DIRECTOR"
ROLE_MEDICAL = "MEDICAL"
ROLE_INSURANCE = "INSURANCE"
ROLE_FINANCE = "FINANCE"
ROLE_VIEWER = "VIEWER"


@dataclass
class CurrentUser:
    user_id: str
    role: str
    dept_name: str | None
    display_name: str | None = None
    auth_source: str = "unknown"


def _normalize_identity_key(value: str) -> str:
    return value.strip().lower()


@lru_cache(maxsize=8)
def _load_user_map_cached(map_path: str, mtime_ns: int) -> dict[str, dict[str, str | None]]:
    _ = mtime_ns
    path = Path(map_path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)

    users = payload.get("users", {})
    if not isinstance(users, dict):
        return {}

    normalized: dict[str, dict[str, str | None]] = {}
    for raw_user_id, raw_info in users.items():
        if not isinstance(raw_user_id, str) or not isinstance(raw_info, dict):
            continue
        normalized[_normalize_identity_key(raw_user_id)] = {
            "role": str(raw_info.get("role") or ROLE_VIEWER).strip().upper() or ROLE_VIEWER,
            "dept_name": str(raw_info.get("dept_name")).strip() if raw_info.get("dept_name") else None,
            "display_name": str(raw_info.get("display_name")).strip() if raw_info.get("display_name") else None,
        }
    return normalized


def _load_user_map(map_path: str) -> dict[str, dict[str, str | None]]:
    path = Path(map_path)
    if not path.exists():
        return {}
    stat = path.stat()
    return _load_user_map_cached(str(path.resolve()), stat.st_mtime_ns)


def _build_dev_header_user(
    x_user_id: str | None,
    x_role: str | None,
    x_dept_name: str | None,
) -> CurrentUser:
    user_id = (x_user_id or "guest").strip() or "guest"
    role = (x_role or ROLE_VIEWER).strip().upper() or ROLE_VIEWER
    dept_name = x_dept_name.strip() if x_dept_name else None
    return CurrentUser(
        user_id=user_id,
        role=role,
        dept_name=dept_name,
        display_name=user_id,
        auth_source="dev_header",
    )


def resolve_current_user_from_request(
    request: Request,
    x_user_id: str | None = None,
    x_role: str | None = None,
    x_dept_name: str | None = None,
) -> CurrentUser:
    settings = get_settings()

    if settings.auth_mode == "dev_header":
        return _build_dev_header_user(x_user_id=x_user_id, x_role=x_role, x_dept_name=x_dept_name)

    trusted_proxy_ips = set(settings.auth_trusted_proxy_ips)
    client_host = request.client.host if request.client else None
    if client_host not in trusted_proxy_ips:
        raise HTTPException(status_code=401, detail="untrusted proxy")

    identity_header = settings.auth_identity_header.strip().lower()
    remote_user = (request.headers.get(identity_header) or "").strip()
    if not remote_user:
        raise HTTPException(status_code=401, detail="missing authenticated user")

    user_map = _load_user_map(settings.auth_user_map_file)
    user_info = user_map.get(_normalize_identity_key(remote_user))
    if user_info is None:
        if not settings.auth_allow_unmapped_viewer:
            raise HTTPException(status_code=403, detail="user not mapped")
        return CurrentUser(
            user_id=remote_user,
            role=ROLE_VIEWER,
            dept_name=None,
            display_name=remote_user,
            auth_source="trusted_header",
        )

    return CurrentUser(
        user_id=remote_user,
        role=str(user_info.get("role") or ROLE_VIEWER).upper(),
        dept_name=user_info.get("dept_name"),
        display_name=user_info.get("display_name") or remote_user,
        auth_source="trusted_header",
    )


def get_current_user(
    request: Request,
    x_user_id: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
    x_dept_name: str | None = Header(default=None),
) -> CurrentUser:
    return resolve_current_user_from_request(
        request=request,
        x_user_id=x_user_id,
        x_role=x_role,
        x_dept_name=x_dept_name,
    )


def require_roles(*allowed_roles: str):
    allowed = {item.upper() for item in allowed_roles}

    def _checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return current_user

    return _checker


def resolve_dept_scope(requested_dept: str | None, current_user: CurrentUser) -> str | None:
    if current_user.role in {ROLE_ADMIN, ROLE_MEDICAL, ROLE_INSURANCE, ROLE_FINANCE}:
        return requested_dept

    if current_user.dept_name:
        if requested_dept and requested_dept != current_user.dept_name:
            raise HTTPException(status_code=403, detail="forbidden dept scope")
        return current_user.dept_name
    return requested_dept
