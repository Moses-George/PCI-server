import os
import logging

logger = logging.getLogger(__name__)

BBOX_MODEL_PATH = os.path.join(os.getcwd(), "app", "vision_models", "bbox_model.pt")
BBOX_MODEL_PATH_EXISTS = os.path.exists(BBOX_MODEL_PATH)
BBOX_MODEL = None


def load_models():
    global BBOX_MODEL

    if not BBOX_MODEL_PATH_EXISTS:
        logger.error(f"Model file not found at {BBOX_MODEL_PATH}")
        raise FileNotFoundError(f"YOLO model not found: {BBOX_MODEL_PATH}")

    from ultralytics import YOLO
    BBOX_MODEL = YOLO(BBOX_MODEL_PATH)
    logger.info(f"Loaded BBOX model from {BBOX_MODEL_PATH}")