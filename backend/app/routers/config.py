from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import ROLE_ADMIN, ROLE_MEDICAL, CurrentUser, get_current_user, require_roles
from app.db.session import get_db
from app.schemas.config import ConfigItemOut, ConfigListOut, ConfigUpsertIn
from app.services.config_service import list_configs, upsert_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigListOut)
def config_list(
    category: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    return list_configs(db=db, category=category)


@router.put("/{config_key}", response_model=ConfigItemOut)
def config_upsert(
    config_key: str,
    payload: ConfigUpsertIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(ROLE_ADMIN, ROLE_MEDICAL)),
):
    return upsert_config(
        db=db,
        config_key=config_key,
        config_value=payload.config_value,
        category=payload.category,
        description=payload.description,
        updated_by=current_user.user_id,
    )
