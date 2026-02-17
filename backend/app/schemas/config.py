from datetime import datetime

from pydantic import BaseModel


class ConfigItemOut(BaseModel):
    config_key: str
    config_value: str
    category: str | None
    description: str | None
    updated_by: str | None
    updated_at: datetime


class ConfigListOut(BaseModel):
    items: list[ConfigItemOut]


class ConfigUpsertIn(BaseModel):
    config_value: str
    category: str | None = None
    description: str | None = None
