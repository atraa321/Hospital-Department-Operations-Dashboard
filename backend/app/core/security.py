from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException


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


def get_current_user(
    x_user_id: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
    x_dept_name: str | None = Header(default=None),
) -> CurrentUser:
    # Intranet MVP: header-based identity to enable role and data-domain controls.
    user_id = (x_user_id or "guest").strip() or "guest"
    role = (x_role or ROLE_VIEWER).strip().upper()
    dept_name = x_dept_name.strip() if x_dept_name else None
    return CurrentUser(user_id=user_id, role=role, dept_name=dept_name)


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
