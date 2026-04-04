from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import subprocess
import sys
import threading
import time

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.import_batch import BatchStatus, ImportBatch


logger = logging.getLogger(__name__)
_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _claim_next_batch() -> str | None:
    with SessionLocal() as db:
      batch = (
          db.execute(
              select(ImportBatch)
              .where(ImportBatch.status.in_([BatchStatus.QUEUED.value, BatchStatus.PENDING.value]))
              .order_by(ImportBatch.created_at.asc())
              .limit(1)
          )
          .scalars()
          .first()
      )
      if batch is None:
          return None
      if batch.cancel_requested_at is not None:
          batch.status = BatchStatus.CANCELED.value
          batch.finished_at = datetime.utcnow()
          batch.error_message = "Import task canceled before execution."
          batch.worker_pid = None
          db.add(batch)
          db.commit()
          return None

      batch.status = BatchStatus.RUNNING.value
      batch.started_at = datetime.utcnow()
      batch.finished_at = None
      batch.error_message = None
      db.add(batch)
      db.commit()
      return batch.batch_id


def _set_worker_pid(batch_id: str, pid: int | None) -> None:
    with SessionLocal() as db:
        batch = db.execute(select(ImportBatch).where(ImportBatch.batch_id == batch_id)).scalars().first()
        if batch is None:
            return
        batch.worker_pid = pid
        db.add(batch)
        db.commit()


def _mark_batch_result(batch_id: str, status: str, message: str) -> None:
    with SessionLocal() as db:
        batch = db.execute(select(ImportBatch).where(ImportBatch.batch_id == batch_id)).scalars().first()
        if batch is None:
            return
        if batch.status in {BatchStatus.SUCCESS.value, BatchStatus.FAILED.value, BatchStatus.CANCELED.value}:
            return
        batch.status = status
        batch.finished_at = datetime.utcnow()
        batch.worker_pid = None
        batch.error_message = message
        db.add(batch)
        db.commit()


def _monitor_process(batch_id: str, proc: subprocess.Popen[str]) -> None:
    settings = get_settings()
    started = time.monotonic()
    timeout_seconds = max(settings.import_task_timeout_seconds, 60)

    while proc.poll() is None and not _stop_event.is_set():
        time.sleep(max(settings.import_queue_poll_seconds, 1))
        with SessionLocal() as db:
            batch = db.execute(select(ImportBatch).where(ImportBatch.batch_id == batch_id)).scalars().first()
            if batch is None:
                proc.terminate()
                return
            if batch.cancel_requested_at is not None:
                proc.terminate()
                proc.wait(timeout=15)
                _mark_batch_result(batch_id, BatchStatus.CANCELED.value, "Import task canceled by operator.")
                return

        if time.monotonic() - started > timeout_seconds:
            proc.kill()
            proc.wait(timeout=15)
            _mark_batch_result(batch_id, BatchStatus.FAILED.value, "Import task timed out.")
            return

    if _stop_event.is_set() and proc.poll() is None:
        proc.terminate()
        return

    if proc.returncode and proc.returncode != 0:
        _mark_batch_result(batch_id, BatchStatus.FAILED.value, f"Import worker exited with code {proc.returncode}.")


def _worker_loop() -> None:
    logger.info("import queue worker started")
    while not _stop_event.is_set():
        batch_id = _claim_next_batch()
        if not batch_id:
            time.sleep(max(get_settings().import_queue_poll_seconds, 1))
            continue

        logger.info("processing queued import batch %s", batch_id)
        proc = subprocess.Popen(
            [sys.executable, "-m", "app.workers.import_worker", "--batch-id", batch_id],
            cwd=str(_backend_root()),
            text=True,
        )
        _set_worker_pid(batch_id, proc.pid)
        _monitor_process(batch_id, proc)
        _set_worker_pid(batch_id, None)
    logger.info("import queue worker stopped")


def start_import_worker() -> None:
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker_loop, name="import-queue-worker", daemon=True)
    _worker_thread.start()


def stop_import_worker() -> None:
    _stop_event.set()
