from pydantic import BaseModel


class CurrentUserOut(BaseModel):
    user_id: str
    role: str
    dept_name: str | None
    display_name: str | None
    auth_source: str
