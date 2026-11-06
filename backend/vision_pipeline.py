from typing import Any, Dict, List
import cv2
import numpy as np
from paddleocr import PaddleOCR

_ocr_engine = None

def init_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        # PaddleOCR 2.7+ removed show_log and deprecated use_angle_cls.
        # Use use_textline_orientation=True for angle classification.
        # Ref: https://wenku.csdn.net/answer/3ek27u35ozs1
        _ocr_engine = PaddleOCR(
            use_textline_orientation=True,
            lang='en',
        )

def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def process_ram_image(image_bytes: bytes) -> List[Dict[str, Any]]:
    global _ocr_engine
    if _ocr_engine is None: init_ocr()
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None: return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rectified = img
    if contours:
        largest = max(contours, key=cv2.contourArea)
        approx = cv2.approxPolyDP(largest, 0.02 * cv2.arcLength(largest, True), True)
        if len(approx) == 4:
            rect = _order_points(approx.reshape(4, 2))
            (tl, tr, br, bl) = rect
            maxW = max(int(np.sqrt(((br[0]-bl[0])**2)+((br[1]-bl[1])**2))), int(np.sqrt(((tr[0]-tl[0])**2)+((tr[1]-tl[1])**2))))
            maxH = max(int(np.sqrt(((tr[0]-br[0])**2)+((tr[1]-br[1])**2))), int(np.sqrt(((tl[0]-bl[0])**2)+((tl[1]-bl[1])**2))))
            dst = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype="float32")
            rectified = cv2.warpPerspective(img, cv2.getPerspectiveTransform(rect, dst), (maxW, maxH))

    # PaddleOCR 2.7.3 accepts cls parameter but ignores it; angle is handled at init.
    result = _ocr_engine.ocr(rectified, cls=True)

    results = []
    if result and result[0]:
        # 2.x return shape: list of [box, (text, confidence)]
        for line in result[0]:
            box, (text, conf) = line
            if conf >= 0.6:
                clean = "".join(c for c in text if c.isalnum() or c in ["-", " ", ":"])
                if len(clean) >= 4:
                    xs, ys = [pt[0] for pt in box], [pt[1] for pt in box]
                    results.append({"bbox": [int(min(xs)), int(min(ys)), int(max(xs)-min(xs)), int(max(ys)-min(ys))], "extracted_text": clean})
    return results
