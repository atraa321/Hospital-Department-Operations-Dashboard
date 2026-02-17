import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import SessionLocal, engine
import app.models  # noqa: F401
from app.services.analytics_service import get_cost_structure, get_cost_trend, get_disease_priority
from app.services.workflow_service import run_detection


def measure(name, fn):
    start = time.perf_counter()
    result = fn()
    cost_ms = (time.perf_counter() - start) * 1000
    print(f"{name}: {cost_ms:.2f} ms")
    return result


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        measure("cost_structure", lambda: get_cost_structure(db))
        measure("cost_trend", lambda: get_cost_trend(db))
        measure("disease_priority", lambda: get_disease_priority(db, limit=50))
        measure("run_detection_1000", lambda: run_detection(db, limit=1000))
    finally:
        db.close()


if __name__ == "__main__":
    main()
