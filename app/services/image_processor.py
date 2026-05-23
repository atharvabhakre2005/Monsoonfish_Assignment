"""
Computer-vision image transformations.

Produces three outputs from a single input image:
  1. silhouette.png  – solid filled shape, no internal detail
  2. border.png      – edge / outline only
  3. grayscale.png   – grayscale conversion

All processing uses OpenCV and NumPy.  Pillow is used only for the
final save so that PNG metadata is clean.
"""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def _decode_image(raw_bytes: bytes) -> np.ndarray:
    """Decode raw file bytes into an OpenCV BGR image (with alpha if present)."""
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("Could not decode the uploaded image — file may be corrupt.")
    return img


def _extract_alpha_or_threshold(img: np.ndarray) -> np.ndarray:
    """
    Return a binary mask representing the foreground region.

    Strategy:
      • If the image has an alpha channel  → use alpha > 0 as the mask.
      • Otherwise → convert to grayscale, apply Otsu thresholding, and
        invert if the background is dark (assume logo is the brighter region
        when there's no transparency info).
    """
    if img.ndim == 3 and img.shape[2] == 4:
        # BGRA — alpha channel is the 4th
        alpha = img[:, :, 3]
        _, mask = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
    else:
        # No alpha — fall back to luminance-based segmentation
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img.copy()

        # Apply Gaussian blur to reduce noise before thresholding
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Otsu automatically picks the best threshold
        _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Heuristic: if more than half the pixels are foreground,
        # we probably inverted the wrong way — flip it.
        if np.count_nonzero(mask) > mask.size * 0.5:
            mask = cv2.bitwise_not(mask)

    return mask


def _save_with_pillow(img_array: np.ndarray, path: Path) -> None:
    """Save a NumPy array (BGR / BGRA / grayscale) as a PNG via Pillow."""
    if img_array.ndim == 3 and img_array.shape[2] == 4:
        pil_img = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_BGRA2RGBA))
    elif img_array.ndim == 3 and img_array.shape[2] == 3:
        pil_img = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB))
    else:
        pil_img = Image.fromarray(img_array)

    pil_img.save(str(path), format="PNG")


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def generate_silhouette(img: np.ndarray, output_path: Path) -> None:
    """
    Produce a solid filled silhouette of the logo.

    The foreground is filled with solid black on a transparent background
    (BGRA output).  No internal detail is preserved — just the outer shape.
    """
    mask = _extract_alpha_or_threshold(img)

    # Clean up small holes / noise with morphological closing
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Fill enclosed contours so the silhouette is truly solid
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)

    # Build a 4-channel image: solid black foreground, transparent background
    h, w = filled.shape
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, 3] = filled  # alpha = filled region

    _save_with_pillow(result, output_path)


def generate_border(img: np.ndarray, output_path: Path) -> None:
    """
    Extract the edges / outline of the logo — lines only, no fills.

    Uses Canny edge detection on the foreground mask so the result
    captures the outer contour and any strong internal strokes.
    """
    mask = _extract_alpha_or_threshold(img)

    # Canny on the mask gives the outer boundary
    edges_mask = cv2.Canny(mask, 50, 150)

    # Also detect edges from the actual image content for internal detail
    if img.ndim == 3:
        gray_content = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray_content = img.copy()

    edges_content = cv2.Canny(gray_content, 80, 200)

    # Combine outer boundary + internal edges, masked to the foreground
    combined = cv2.bitwise_or(edges_mask, edges_content)

    # Slightly dilate so thin strokes are visible
    kernel = np.ones((2, 2), np.uint8)
    combined = cv2.dilate(combined, kernel, iterations=1)

    # White edges on transparent background
    h, w = combined.shape
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[combined > 0] = [255, 255, 255, 255]

    _save_with_pillow(result, output_path)


def generate_grayscale(img: np.ndarray, output_path: Path) -> None:
    """
    Convert the image to grayscale while preserving alpha transparency.
    """
    has_alpha = img.ndim == 3 and img.shape[2] == 4

    if img.ndim == 3:
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    if has_alpha:
        # Preserve original alpha
        alpha = img[:, :, 3]
        h, w = gray.shape
        result = np.zeros((h, w, 4), dtype=np.uint8)
        result[:, :, 0] = gray  # B
        result[:, :, 1] = gray  # G
        result[:, :, 2] = gray  # R
        result[:, :, 3] = alpha
        _save_with_pillow(result, output_path)
    else:
        _save_with_pillow(gray, output_path)


def process_image(raw_bytes: bytes, output_dir: Path) -> dict[str, Path]:
    """
    Run all three transformations and return a dict of output paths.

    Raises ValueError if the image cannot be decoded.
    """
    img = _decode_image(raw_bytes)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {
        "silhouette": output_dir / "silhouette.png",
        "border": output_dir / "border.png",
        "grayscale": output_dir / "grayscale.png",
    }

    generate_silhouette(img, paths["silhouette"])
    generate_border(img, paths["border"])
    generate_grayscale(img, paths["grayscale"])

    return paths
