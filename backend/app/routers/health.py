from sqlalchemy import text
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}

