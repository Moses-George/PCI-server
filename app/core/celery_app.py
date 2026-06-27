from celery import Celery
from celery.signals import worker_process_init
import logging

logger = logging.getLogger(__name__)

celery_app = Celery(
    "pci_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.tasks.yolo_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # only ack after task completes, safer on crashes
    worker_prefetch_multiplier=1,  # don't prefetch — YOLO tasks are heavy
)


@worker_process_init.connect
def load_models_on_worker_start(**kwargs):
    """
    Each Celery worker process loads its own model copy.
    This runs once per worker process at startup, not per task.
    """
    logger.info("Worker process starting — loading YOLO model...")
    from app.core.models import load_models
    load_models()
    logger.info("YOLO model loaded successfully.")