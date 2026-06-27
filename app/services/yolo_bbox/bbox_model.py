import os
from dataclasses import dataclass, field
from typing import Dict, List
import time
from app.core.models import BBOX_MODEL, BBOX_MODEL_PATH
import cv2
from app.services.yolo_bbox.width_estimator import CrackWidthEstimator
from app.utils.config_bbox import CLASS_NAMES, bbox_cfg


@dataclass
class DistressRecord:
    """One distress instance detected in a sample unit."""

    class_name: str
    severity: str  # "low" | "medium" | "high" | "n/a"
    width_mm: float = 0.0  # for linear cracks
    length_mm: float = 0.0  # for linear cracks
    area_mm2: float = 0.0  # for area distresses
    confidence: float = 0.0
    bbox: List[int] = field(default_factory=list)

    # ------------------------------------------------------------------


def infer_image_bbox_model(image_path, px_per_mm: float):
    """
    Run the full pipeline on a single BGR image.

    Returns
    -------
    annotated_image : np.ndarray
    result          : DetectionResult
    """
    if not BBOX_MODEL_PATH:
        return

    est = CrackWidthEstimator(px_per_mm)

    t0 = time.time()
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise ValueError(f"Could not load image at {image_path}")
    h, w = image_bgr.shape[:2]
    # annotated = image_bgr.copy()

    # ── Phase I: YOLOv8 Detection ─────────────────────────────────
    yolo_results = BBOX_MODEL.predict(
        source=image_bgr,
        imgsz=bbox_cfg.img_size,
        conf=bbox_cfg.CONF_THRESHOLD,
        iou=bbox_cfg.IOU_THRESHOLD,
        # device=bbox_cfg,
    )
    # print(yolo_results[0])
    annotated = yolo_results[0].plot()

    detections: List[Dict] = []
    records: List[DistressRecord] = []

    if yolo_results and yolo_results[0].boxes is not None:
        print("yes")
        boxes = yolo_results[0].boxes
        # print(boxes)
        xyxy = boxes.xyxy.cpu().numpy()  # [N, 4]
        confs = boxes.conf.cpu().numpy()  # [N]
        clsids = boxes.cls.cpu().numpy().astype(int)  # [N]

        for i in range(len(xyxy)):
            x1, y1, x2, y2 = map(int, xyxy[i])
            conf_val = float(confs[i])
            cls_id = int(clsids[i])
            cls_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else "unknown"

            # ── Phase II: Width estimation ────────────────────────
            crop = image_bgr[max(0, y1) : min(h, y2), max(0, x1) : min(w, x2)]
            width_result = est.estimate(crop, class_name=cls_name)

            width_mm = width_result["width_mm"]
            length_mm = width_result["length_mm"]
            area_mm2 = width_result["area_mm2"]
            severity = width_result["severity"]

            det_dict = {
                "class_id": cls_id,
                "class_name": cls_name,
                "confidence": conf_val,
                "bbox": [x1, y1, x2, y2],
                "width_mm": width_mm,
                "length_mm": length_mm,
                "area_mm2": area_mm2,
                "severity": severity,
                "severity_label": width_result["severity_label"],
            }
            detections.append(det_dict)
            records.append(
                DistressRecord(
                    class_name=cls_name,
                    severity=severity,
                    width_mm=width_mm,
                    length_mm=length_mm,
                    area_mm2=area_mm2,
                    bbox=[x1, y1, x2, y2],
                    confidence=conf_val,
                )
            )

    return detections, records, annotated
