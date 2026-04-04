from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.schemas.auth import CurrentUserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUserOut)
def auth_me(current_user: CurrentUser = Depends(get_current_user)):
    return CurrentUserOut.model_validate(current_user.__dict__)
