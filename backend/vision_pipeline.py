from typing import Any, Dict, List
import cv2
import numpy as np
from paddleocr import PaddleOCR

_ocr_engine = None

def init_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        # PaddleOCR 2.7+ removed show_log and deprecated use_angle_cls
        _ocr_engine = PaddleOCR(use_textline_orientation=True, lang='en', enable_mkldnn=False)

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

def process_ram_image(image_bytes: bytes) -> List[Dict[str, Any]]:
    global _ocr_engine
    if _ocr_engine is None:
        init_ocr()

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rectified = img
    if contours:
        largest = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
        if len(approx) == 4:
            rectified = _perspective_warp(img, approx.reshape(4, 2))

    # cls=True was removed in 2.7+, but we pass it to ensure compatibility if fallback is used
    try:
        result = _ocr_engine.ocr(rectified, cls=True)
    except TypeError:
        result = _ocr_engine.ocr(rectified)

    results: List[Dict[str, Any]] = []
    if result and result[0]:
        # Handle both dict (3.x) and nested list (2.x) outputs
        if isinstance(result[0], dict):
            texts = result[0].get("rec_texts", [])
            scores = result[0].get("rec_scores", [])
            boxes = result[0].get("rec_boxes", [])
            for i, text in enumerate(texts):
                if float(scores[i]) < 0.60:
                    continue
                clean = "".join(c for c in text if c.isalnum() or c in ["-", " ", ":"])
                if len(clean) >= 4:
                    box = boxes[i]
                    results.append({
                        "bbox": [int(box[0]), int(box[1]), int(box[2]-box[0]), int(box[3]-box[1])],
                        "extracted_text": clean
                    })
        else:
            for line in result[0]:
                box, (text, conf) = line
                if conf < 0.60:
                    continue
                clean = "".join(c for c in text if c.isalnum() or c in ["-", " ", ":"])
                if len(clean) >= 4:
                    xs = [pt[0] for pt in box]
                    ys = [pt[1] for pt in box]
                    results.append({
                        "bbox": [int(min(xs)), int(min(ys)), int(max(xs)-min(xs)), int(max(ys)-min(ys))],
                        "extracted_text": clean
                    })
    return results
