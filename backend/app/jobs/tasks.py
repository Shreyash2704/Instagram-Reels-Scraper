"""RQ job entrypoints (importable by worker process)."""

import logging

from app.db.session import session_factory
from app.services.pipeline_service import execute_run

log = logging.getLogger(__name__)


def process_run(run_id: int) -> None:
    """Execute pipeline for a run (same logic as in-process background task)."""
    db = session_factory()
    try:
        log.info("[rq] process_run run_id=%s", run_id)
        execute_run(db, run_id)
    finally:
        db.close()
