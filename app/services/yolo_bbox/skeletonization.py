from typing import Callable, Dict, List, Optional, Tuple
import numpy as np
from skimage.filters import sato 
from skimage.morphology import skeletonize as ski_skeletonize
import cv2
from app.utils.config_bbox import bbox_cfg

SEVERITY_LOW_MAX = 5.0  # mm  (paper Table 1)
SEVERITY_MEDIUM_MAX = 20.0  # mm

SEVERITY_LABELS = {
    "low": f"Low (<{SEVERITY_LOW_MAX} mm)",
    "medium": f"Medium ({SEVERITY_LOW_MAX}–{SEVERITY_MEDIUM_MAX} mm)",
    "high": f"High (>{SEVERITY_MEDIUM_MAX} mm)",
    "n/a": "N/A (non-linear distress)",
}


# ─────────────────────────────────────────────────────────────────────────────
# Sato Tubeness (Hessian-based) segmentation
# ─────────────────────────────────────────────────────────────────────────────


def _sato_skimage(gray: np.ndarray, sigmas: List[float]) -> np.ndarray:
    """
    Sato Tubeness filter via scikit-image.
    Returns float32 response map in [0, 1].

    Paper Eq. 1–3:
        H(i,j,σ) = Hessian at each pixel & scale
        R(i,j,σ) = σ² · max(λ₁, 0)           [Eq. 2]
        F(i,j)   = max_σ R(i,j,σ)             [Eq. 3]
    """
    gray_f = gray.astype(np.float32) / 255.0
    result = sato(gray_f, sigmas=sigmas, black_ridges=True)
    # Normalise to [0, 1]
    if result.max() > 0:
        result = result / result.max()
    return result.astype(np.float32)


def _sato_opencv(gray: np.ndarray, sigmas: List[float]) -> np.ndarray:
    """
    Pure-OpenCV approximation of the Sato filter (Hessian eigenvalues via
    second-order Gaussian derivatives).  Less accurate than skimage but
    available without scikit-image.
    """
    gray_f = gray.astype(np.float32) / 255.0
    max_response = np.zeros_like(gray_f)

    for sigma in sigmas:
        ksize = max(3, int(6 * sigma + 1) | 1)  # ensure odd
        # Smooth
        blurred = cv2.GaussianBlur(gray_f, (ksize, ksize), sigma)
        # Second-order derivatives
        Lxx = cv2.Sobel(blurred, cv2.CV_32F, 2, 0, ksize=3)
        Lyy = cv2.Sobel(blurred, cv2.CV_32F, 0, 2, ksize=3)
        Lxy = cv2.Sobel(blurred, cv2.CV_32F, 1, 1, ksize=3)

        # Hessian eigenvalues
        trace = Lxx + Lyy
        det = Lxx * Lyy - Lxy**2
        disc = np.sqrt(np.maximum((trace**2 / 4) - det, 0))
        lambda1 = trace / 2 + disc
        # lambda2 = trace / 2 - disc

        # Response R = σ² · max(λ₁, 0)   [Eq. 2]
        R = (sigma**2) * np.maximum(lambda1, 0)
        max_response = np.maximum(max_response, R)  # Eq. 3

    if max_response.max() > 0:
        max_response = max_response / max_response.max()
    return max_response.astype(np.float32)


def sato_tubeness(
    gray: np.ndarray,
    sigmas: Optional[List[float]] = None,
) -> np.ndarray:
    """
    Compute the Sato Tubeness response, using skimage if available,
    falling back to the pure-OpenCV implementation.
    """
    sigmas = [1, 2, 3, 4, 5, 6, 8, 10]
    return _sato_skimage(gray, sigmas)
    # if sigmas is None:
    #     sigmas = [1, 2, 3, 4, 5, 6, 8, 10]
    # if _SKIMAGE_AVAILABLE:
    #     return _sato_skimage(gray, sigmas)
    # return _sato_opencv(gray, sigmas)


# ─────────────────────────────────────────────────────────────────────────────
# Morphological operations  (paper Eq. 4–6)
# ─────────────────────────────────────────────────────────────────────────────


def morphological_refine(
    binary: np.ndarray,
    dilation_k: int = 3,
    erosion_k: int = 3,
    opening_k: int = 3,
) -> np.ndarray:
    """
    Apply dilation → erosion → opening to refine binary crack segmentation.

    Paper Eq. 4 : dilation  A ⊕ B  – connect fragmented cracks
    Paper Eq. 5 : erosion   A ⊖ B  – remove small noise
    Paper Eq. 6 : opening   (A ⊖ B) ⊕ B – smooth crack contours
    """
    d_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (dilation_k, dilation_k))
    e_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (erosion_k, erosion_k))
    o_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (opening_k, opening_k))

    out = cv2.dilate(binary, d_kern, iterations=1)  # Eq. 4
    out = cv2.erode(out, e_kern, iterations=1)  # Eq. 5
    out = cv2.morphologyEx(out, cv2.MORPH_OPEN, o_kern)  # Eq. 6
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Skeleton algorithm  (paper Section 3.2.2)
# ─────────────────────────────────────────────────────────────────────────────


def skeletonize(binary: np.ndarray) -> np.ndarray:
    """
    Parallel iterative thinning (Zhang-Suen / Guo-Hall) to reduce the binary
    crack mask to a 1-pixel-wide skeleton.

    Paper reference: Guo & Hall (1989) – parallel thinning with two
    sub-iteration algorithms.

    Returns uint8 binary skeleton (255 = skeleton pixel).
    """
    # if _SKIMAGE_AVAILABLE:
    # Use scikit-image's optimised implementation
    bool_mask = binary > 0
    skel = ski_skeletonize(bool_mask)
    return skel.astype(np.uint8) * 255
    # else:
    #     # OpenCV iterative thinning
    #     return _opencv_thin(binary)


# def _opencv_thin(binary: np.ndarray) -> np.ndarray:
#     """Zhang-Suen thinning via OpenCV's ximgproc (if available) or manual loop."""
#     try:
#         import cv2.ximgproc as xip

#         thin = xip.thinning(binary, thinningType=xip.THINNING_ZHANGSUEN)
#         return thin
#     except (ImportError, AttributeError):
#         return _manual_thin(binary)


def _manual_thin(binary: np.ndarray) -> np.ndarray:
    """Pure-NumPy Zhang-Suen thinning (fallback)."""
    img = (binary > 0).astype(np.uint8)
    prev = np.zeros_like(img)
    while not np.array_equal(img, prev):
        prev = img.copy()
        for iteration in range(2):
            marked = np.zeros_like(img)
            for y in range(1, img.shape[0] - 1):
                for x in range(1, img.shape[1] - 1):
                    p2 = img[y - 1, x]
                    p3 = img[y - 1, x + 1]
                    p4 = img[y, x + 1]
                    p5 = img[y + 1, x + 1]
                    p6 = img[y + 1, x]
                    p7 = img[y + 1, x - 1]
                    p8 = img[y, x - 1]
                    p9 = img[y - 1, x - 1]
                    s = (
                        int(p2 == 0 and p3 == 1)
                        + int(p3 == 0 and p4 == 1)
                        + int(p4 == 0 and p5 == 1)
                        + int(p5 == 0 and p6 == 1)
                        + int(p6 == 0 and p7 == 1)
                        + int(p7 == 0 and p8 == 1)
                        + int(p8 == 0 and p9 == 1)
                        + int(p9 == 0 and p2 == 1)
                    )
                    n = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
                    if img[y, x] and 2 <= n <= 6 and s == 1:
                        if iteration == 0 and not (p2 and p4 and p6):
                            marked[y, x] = 1
                        elif iteration == 1 and not (p2 and p4 and p8):
                            marked[y, x] = 1
            img[marked == 1] = 0
    return (img * 255).astype(np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# Width Estimation  (paper Eq. 7)
# ─────────────────────────────────────────────────────────────────────────────


def compute_width(
    binary_mask: np.ndarray,
    skeleton: np.ndarray,
    px_per_mm: float = 1.0,
) -> Tuple[float, float, float]:
    """
    W = A / B  (paper Eq. 7)
      A = number of pixels in crack (binary_mask)
      B = number of pixels in skeleton

    Returns (width_mm, length_mm, area_mm2).
    """
    A = float(np.count_nonzero(binary_mask))  # crack pixel count
    B = float(np.count_nonzero(skeleton))  # skeleton pixel count

    if B == 0:
        return 0.0, 0.0, 0.0

    width_px = A / B  # Eq. 7
    width_mm = width_px / px_per_mm
    length_mm = B / px_per_mm  # skeleton = 1-px path ≈ length
    area_mm2 = A / (px_per_mm**2)

    return width_mm, length_mm, area_mm2


# ─────────────────────────────────────────────────────────────────────────────
# Severity classification
# ─────────────────────────────────────────────────────────────────────────────


def classify_severity(width_mm: float, class_name: str) -> str:
    """
    Assign severity for width-based distress types (long./transverse/edge).
    Area-based types (alligator, patching, pothole, rutting) return 'n/a'.
    """
    if class_name.lower() not in bbox_cfg.width_severity_types:
        return "n/a"

    if width_mm < SEVERITY_LOW_MAX:
        return "low"
    elif width_mm <= SEVERITY_MEDIUM_MAX:
        return "medium"
    else:
        return "high"
