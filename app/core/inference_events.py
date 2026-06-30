import json
from app.core.redis_client import sync_redis


def publish_inference_event(sample_unit_id: str, event: dict):
    """
    Publish a progress event from the Celery worker.
    The FastAPI WS picks this up and forwards to the frontend.
    """
    channel = f"inference:{sample_unit_id}"
    sync_redis.publish(channel, json.dumps(event))


# ── Convenience helpers ───────────────────────────────────────────────────────


def publish_processing(sample_unit_id: str, step: str, detail: str = ""):
    publish_inference_event(
        sample_unit_id,
        {
            "status": "processing",
            "step": step,
            "detail": detail,
        },
    )


def publish_done(sample_unit_id: str, detection_count: int):
    publish_inference_event(
        sample_unit_id,
        {
            "status": "done",
            "step": "complete",
            "detection_count": detection_count,
        },
    )


def publish_failed(sample_unit_id: str, detail: str):
    publish_inference_event(
        sample_unit_id,
        {
            "status": "failed",
            "step": "error",
            "detail": detail,
        },
    )
