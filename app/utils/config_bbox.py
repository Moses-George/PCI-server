from typing import Dict, List, Tuple


class Config:
    img_size = 640
    # device = "cuda" if torch.cuda.is_available() else "cpu"

    IOU_THRESHOLD = 0.25
    CONF_THRESHOLD = 0.25

    # width_estimation
    # Sato Tubeness scales (σ range for Hessian multi-scale analysis)
    sato_sigmas = [1, 2, 3, 4, 5, 6, 8, 10]
    # Morphological kernel sizes
    dilation_kernel = 3
    erosion_kernel = 3
    opening_kernel = 3

    # Severity thresholds per paper Table 1 (mm)
    severity_low_max = 5.0  # <5 mm  → Low
    severity_medium_max = 20.0  # 5–20   → Medium
    # >20    → High

    # ── PCI Calculation (ASTM D6433-18) ───────────────────────────
    # Distress types that use width-based severity
    width_severity_types = [
        "longitudinal cracking",
        "transverse cracking",
        "edge cracking",
    ]

    # Area-based distress types
    area_severity_types = ["alligator cracking", "patching", "pothole", "rutting"]


bbox_cfg = Config()

CLASS_NAMES: List[str] = [
    "alligator cracking",  # 0
    "edge cracking",  # 1
    "longitudinal cracking",  # 2
    "patching",  # 3
    "pothole",  # 4
    "rutting",  # 5
    "transverse cracking",  # 6
]

CLASS_MAP: Dict[str, int] = {c: i for i, c in enumerate(CLASS_NAMES)}

WIDTH_SEVERITY_CLASSES = {2, 6, 1}  # longitudinal, transverse, edge
# Distress types that use area/extent-based severity
AREA_SEVERITY_CLASSES = {0, 3, 4, 5}  # alligator, patching, pothole, rutting

# BGR colours for bounding boxes (paper Figure 6 style)
CLASS_COLORS_BGR = {
    "alligator cracking": (0, 0, 255),  # red
    "edge cracking": (0, 165, 255),  # orange
    "longitudinal cracking": (255, 128, 0),  # blue-orange
    "patching": (0, 255, 255),  # yellow
    "pothole": (128, 0, 128),  # purple
    "rutting": (0, 200, 0),  # green
    "transverse cracking": (0, 255, 0),  # bright green
}

SEVERITY_TEXT_COLORS = {
    "low": (100, 200, 100),
    "medium": (0, 165, 255),
    "high": (0, 0, 255),
    "n/a": (200, 200, 200),
}
