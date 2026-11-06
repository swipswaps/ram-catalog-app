from typing import Any, Dict, List

import cv2
import numpy as np
import pytesseract

# JEDEC DDR4 UDIMM nominal dimensions (used to scale bounding-box filters).
DIMM_LENGTH_MM = 133.35
DIMM_HEIGHT_MM = 31.25
MIN_IC_FRACTION = 0.04
MAX_IC_FRACTION = 0.15


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _perspective_warp(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))
    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def _upscale_for_ocr(roi: np.ndarray, target_height: int = 64) -> np.ndarray:
    h, w = roi.shape[:2]
    if h == 0:
        return roi
    scale = max(1.0, target_height / float(h))
    return cv2.resize(roi, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)


def _best_ocr(roi: np.ndarray) -> str:
    candidates = []
    for psm in (6, 7, 8):
        try:
            txt = pytesseract.image_to_string(
                roi,
                config=f"--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
            ).strip()
        except Exception:
            txt = ""
        clean = "".join(c for c in txt if c.isalnum() or c in ["-", ":"])
        candidates.append(clean)
    return max(candidates, key=len) if candidates else ""


def process_ram_image(image_bytes: bytes) -> List[Dict[str, Any]]:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rectified = gray
    board_w, board_h = gray.shape[1], gray.shape[0]
    if contours:
        largest = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
        if len(approx) == 4:
            rectified = _perspective_warp(gray, approx.reshape(4, 2))
            board_w, board_h = rectified.shape[1], rectified.shape[0]

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(rectified)

    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    component_contours, hierarchy = cv2.findContours(
        closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    # Hierarchy filter: keep top-level and one-level-deep contours;
    # drop anything nested deeper (text inside IC bodies).
    if hierarchy is not None:
        hierarchy = hierarchy[0]
        keep = []
        for idx, cnt in enumerate(component_contours):
            parent = hierarchy[idx][3]
            grandparent = hierarchy[parent][3] if parent != -1 else -1
            if grandparent != -1:
                continue
            keep.append(cnt)
        component_contours = keep

    min_w = int(board_w * MIN_IC_FRACTION)
    max_w = int(board_w * MAX_IC_FRACTION)
    min_h = int(board_h * MIN_IC_FRACTION)
    max_h = int(board_h * MAX_IC_FRACTION)

    results: List[Dict[str, Any]] = []
    seen_boxes: List[tuple] = []
    for cnt in component_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if h == 0 or w < min_w or w > max_w or h < min_h or h > max_h:
            continue
        if w > board_w * 0.9 and h > board_h * 0.9:
            continue
        cx, cy = x + w / 2.0, y + h / 2.0
        duplicate = False
        for (sx, sy, sw, sh) in seen_boxes:
            if abs(cx - (sx + sw / 2.0)) < 10 and abs(cy - (sy + sh / 2.0)) < 10:
                duplicate = True
                break
        if duplicate:
            continue
        seen_boxes.append((x, y, w, h))

        roi = enhanced[y : y + h, x : x + w]
        roi_inv = cv2.bitwise_not(roi)
        roi_up = _upscale_for_ocr(roi_inv, target_height=64)
        best = _best_ocr(roi_up)
        if len(best) >= 4:
            results.append({"bbox": [int(x), int(y), int(w), int(h)], "extracted_text": best})

    return results
