from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig


def list_configs(db: Session, category: str | None = None) -> dict:
    stmt = select(SystemConfig)
    if category:
        stmt = stmt.where(SystemConfig.category == category)
    rows = db.execute(stmt.order_by(SystemConfig.config_key.asc())).scalars().all()
    return {
        "items": [
            {
                "config_key": row.config_key,
                "config_value": row.config_value,
                "category": row.category,
                "description": row.description,
                "updated_by": row.updated_by,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    }


def upsert_config(
    db: Session,
    config_key: str,
    config_value: str,
    category: str | None,
    description: str | None,
    updated_by: str | None,
) -> dict:
    item = db.execute(
        select(SystemConfig).where(SystemConfig.config_key == config_key)
    ).scalar_one_or_none()
    if not item:
        item = SystemConfig(config_key=config_key, config_value=config_value)
        db.add(item)

    item.config_value = config_value
    item.category = category
    item.description = description
    item.updated_by = updated_by
    db.commit()
    db.refresh(item)

    return {
        "config_key": item.config_key,
        "config_value": item.config_value,
        "category": item.category,
        "description": item.description,
        "updated_by": item.updated_by,
        "updated_at": item.updated_at,
    }
