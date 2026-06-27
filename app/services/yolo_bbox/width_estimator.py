from typing import Dict, List, Optional
import cv2
import numpy as np
from app.services.yolo_bbox.skeletonization import (
    SEVERITY_LABELS,
    classify_severity,
    compute_width,
    morphological_refine,
    sato_tubeness,
    skeletonize,
)


class CrackWidthEstimator:
    """
    End-to-end crack measurement pipeline (paper Section 3.2).

    Parameters
    ----------
    sigmas      : Sato Tubeness scales
    dilation_k  : dilation kernel size (morphological)
    erosion_k   : erosion kernel size
    opening_k   : opening kernel size
    threshold   : binarisation threshold for the Sato response map
    px_per_mm   : camera calibration (paper: 1 px = 1 mm)
    """

    def __init__(
        self,
        sigmas: Optional[List[float]] = None,
        dilation_k: int = 3,
        erosion_k: int = 3,
        opening_k: int = 3,
        threshold: float = 0.1,
        px_per_mm: float = 1.0,
    ):
        self.sigmas = sigmas or [1, 2, 3, 4, 5, 6, 8, 10]
        self.dilation_k = dilation_k
        self.erosion_k = erosion_k
        self.opening_k = opening_k
        self.threshold = threshold
        self.px_per_mm = px_per_mm

    # ------------------------------------------------------------------
    def estimate(
        self,
        crop_bgr: np.ndarray,
        class_name: str,
    ) -> Dict:
        """
        Run the full width estimation pipeline on a cropped BGR patch.

        Returns
        -------
        dict with keys:
          width_mm, length_mm, area_mm2, severity,
          binary_mask (uint8), skeleton (uint8),
          sato_response (float32)
        """
        if crop_bgr is None or crop_bgr.size == 0:
            return self._empty_result()

        # ── Step 1: Grayscale ──────────────────────────────────────────
        if crop_bgr.ndim == 3:
            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop_bgr.copy()

        # ── Step 2: Sato Tubeness filter (Eq. 1–3) ─────────────────────
        sato_resp = sato_tubeness(gray, self.sigmas)

        # ── Step 3: Binarise ───────────────────────────────────────────
        binary = (sato_resp > self.threshold).astype(np.uint8) * 255

        # ── Step 4: Morphological refinement (Eq. 4–6) ─────────────────
        binary_refined = morphological_refine(
            binary, self.dilation_k, self.erosion_k, self.opening_k
        )

        # ── Step 5: Skeletonize (Section 3.2.2) ───────────────────────
        skeleton = skeletonize(binary_refined)

        # ── Step 6: Width, length, area (Eq. 7) ───────────────────────
        width_mm, length_mm, area_mm2 = compute_width(
            binary_refined, skeleton, self.px_per_mm
        )

        # ── Step 7: Severity ───────────────────────────────────────────
        severity = classify_severity(width_mm, class_name)

        return {
            "width_mm": width_mm,
            "length_mm": length_mm,
            "area_mm2": area_mm2,
            "severity": severity,
            "severity_label": SEVERITY_LABELS.get(severity, severity),
            "binary_mask": binary_refined,
            "skeleton": skeleton,
            "sato_response": sato_resp,
            "class_name": class_name,
        }

        # ------------------------------------------------------------------

    def _empty_result(self) -> Dict:
        return {
            "width_mm": 0.0,
            "length_mm": 0.0,
            "area_mm2": 0.0,
            "severity": "n/a",
            "severity_label": "N/A",
            "binary_mask": np.zeros((1, 1), dtype=np.uint8),
            "skeleton": np.zeros((1, 1), dtype=np.uint8),
            "sato_response": np.zeros((1, 1), dtype=np.float32),
            "class_name": "",
        }
