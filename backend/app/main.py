from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.schema import ensure_case_info_basic_columns, ensure_import_batch_columns
from app.db.session import engine
import app.models  # noqa: F401
from app.routers.alerts import alert_router, workorder_router
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.config import router as config_router
from app.routers.director import router as director_router
from app.routers.dip import router as dip_router
from app.routers.health import router as health_router
from app.routers.imports import router as imports_router
from app.routers.operations import router as operations_router
from app.routers.quality import router as quality_router
from app.routers.reports import router as reports_router
from app.routers.records import router as records_router
from app.services.import_queue import start_import_worker, stop_import_worker

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Path(settings.data_root).mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.export_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
    if settings.db_bootstrap_on_startup:
        Base.metadata.create_all(bind=engine)
    if settings.db_schema_guards_on_startup:
        ensure_case_info_basic_columns(engine)
        ensure_import_batch_columns(engine)
    start_import_worker()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_import_worker()


@app.middleware("http")
async def audit_middleware(request, call_next):
    response = await call_next(request)
    write_audit_log(request, response.status_code)
    return response


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(quality_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(dip_router, prefix="/api/v1")
app.include_router(director_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(alert_router, prefix="/api/v1")
app.include_router(workorder_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(records_router, prefix="/api/v1")
