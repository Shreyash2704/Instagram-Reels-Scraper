"""Redis RQ queue helper.

RQ is imported only when enqueueing so the API can start on Windows with
``REDIS_URL`` unset (BackgroundTasks path) without loading RQ.
"""

from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.jobs.tasks import process_run

if TYPE_CHECKING:
    from rq.queue import Queue


def get_queue() -> "Queue":
    from redis import Redis
    from rq import Queue

    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    return Queue(settings.rq_queue_name, connection=conn)


def enqueue_run(run_id: int) -> None:
    q = get_queue()
    q.enqueue(process_run, run_id)
