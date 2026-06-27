import logging
from pathlib import Path
from celery.exceptions import SoftTimeLimitExceeded
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _mark_failed(sample_unit_id: str):
    """Helper to mark a sample unit as failed in a fresh DB session."""
    from app.core.database import SyncSessionLocal
    from app.models.sample_unit import SampleUnit

    try:
        with SyncSessionLocal() as db:
            sample = db.get(SampleUnit, sample_unit_id)
            if sample:
                sample.inference_status = "failed"
                db.commit()
    except Exception:
        logger.exception(f"Could not mark {sample_unit_id} as failed")


@celery_app.task(
    bind=True,
    max_retries=3,
    time_limit=180,  # hard kill after 3 min
    soft_time_limit=150,  # graceful signal at 2.5 min
    name="tasks.run_yolo_inference",
)
def run_yolo_inference(self, sample_unit_id: str):
    """
    Celery runs in a separate process — must use a sync DB session,
    not the async one FastAPI uses.
    """
    from app.core.celery_app import celery_app
    from app.core.database import SyncSessionLocal  # see note below
    from app.models.sample_unit import SampleUnit
    from app.models.detection_result import DetectionResult
    from app.services.pci.pci_utilities import normalizeClass
    from app.services.yolo_bbox.bbox_model import infer_image_bbox_model
    import cv2

    logger.info(f"Starting inference for sample_unit_id={sample_unit_id}")

    try:
        with SyncSessionLocal() as db:
            sample = db.get(SampleUnit, sample_unit_id)
            if not sample:
                return {"status": "error", "detail": "Sample unit not found"}

            # Mark as processing
            sample.inference_status = "processing"
            db.commit()

            # Run YOLO (blocking is fine here — we're in a worker process)
            detections, records, annotated = infer_image_bbox_model(
                sample.original_image, sample.pixel_to_mm_factor
            )

            if len(detections) == 0:
                # sample.predicted_image = annotated_path
                sample.inference_status = "done"
                db.commit()
                return {"status": "done", "sample_unit_id": sample_unit_id}

            # Save annotated image
            # annotated_path = sample.original_image.replace("original", "predicted")
            # cv2.imwrite(annotated_path, annotated)

            # Persist detections
            for record in records:
                det = DetectionResult(
                    sample_unit_id=sample.id,
                    distress_type=record.class_name,
                    severity=record.severity,
                    quantity=record.count,
                    confidence=record.confidence,
                    normalized_class=normalizeClass(record.class_name),
                    metrics={
                        "avg_width": record.width_mm,
                        "length": record.length_mm,
                        "area": record.area_mm2,
                        "perimeter": 0.0,
                    },
                )
                db.add(det)

            # sample.predicted_image = annotated_path
            sample.inference_status = "done"
            db.commit()

            return {"status": "done", "sample_unit_id": sample_unit_id}

    except SoftTimeLimitExceeded:
        logger.error(f"Soft time limit exceeded for {sample_unit_id}")
        _mark_failed(sample_unit_id)
        # Don't retry on timeout — the image is probably corrupt/too large
        return {"status": "failed", "detail": "Inference timed out"}

    except Exception as exc:
        logger.exception(f"Inference failed for {sample_unit_id}: {exc}")

        if self.request.retries >= self.max_retries:
            # All retries exhausted
            logger.error(f"All retries exhausted for {sample_unit_id}")
            _mark_failed(sample_unit_id)
            return {"status": "failed", "detail": str(exc)}

        # Exponential backoff: 2s, 4s, 8s
        raise self.retry(exc=exc, countdown=2**self.request.retries)
