import logging
import os
import time

from celery import Celery
from celery.app.control import Control, Inspect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery app configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

app = Celery("tasks", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# Auto-scaling configuration
MIN_WORKERS = int(os.getenv("MIN_WORKERS", 2))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 10))
SCALE_UP_THRESHOLD = int(os.getenv("SCALE_UP_THRESHOLD", 100))
SCALE_DOWN_THRESHOLD = int(os.getenv("SCALE_DOWN_THRESHOLD", 10))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))


def get_queue_length():
    inspect = app.control.inspect()
    active_queues = inspect.active_queues()
    if not active_queues:
        return 0

    total_messages = sum(
        len(queue["messages"])
        for worker_queues in active_queues.values()
        for queue in worker_queues
    )
    return total_messages


def scale_workers(current_workers, target_workers):
    control = Control(app)
    if target_workers > current_workers:
        for _ in range(target_workers - current_workers):
            control.pool_grow(1)
            logger.info(f"Scaled up: {current_workers + 1} workers")
    elif target_workers < current_workers:
        for _ in range(current_workers - target_workers):
            control.pool_shrink(1)
            logger.info(f"Scaled down: {current_workers - 1} workers")


def auto_scale():
    while True:
        queue_length = get_queue_length()
        current_workers = len(app.control.inspect().active())

        if queue_length > SCALE_UP_THRESHOLD and current_workers < MAX_WORKERS:
            target_workers = min(current_workers + 1, MAX_WORKERS)
            scale_workers(current_workers, target_workers)
        elif queue_length < SCALE_DOWN_THRESHOLD and current_workers > MIN_WORKERS:
            target_workers = max(current_workers - 1, MIN_WORKERS)
            scale_workers(current_workers, target_workers)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    auto_scale()
