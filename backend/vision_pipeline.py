from typing import Any, Dict, List
import cv2
import numpy as np
from paddleocr import PaddleOCR

_ocr_engine = None

def init_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

def _order_points(pts: np.ndarray) -> np.ndarray:
    # Standard 4-point perspective ordering algorithm.
    # Ref: https://pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example/
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
        # Find the largest 4-point contour (the RAM board) and warp it.
        # Ref: https://pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example/
        approx = cv2.approxPolyDP(max(contours, key=cv2.contourArea), 0.02 * cv2.arcLength(max(contours, key=cv2.contourArea), True), True)
        if len(approx) == 4:
            rect = _order_points(approx.reshape(4, 2))
            (tl, tr, br, bl) = rect
            maxW = max(int(np.sqrt(((br[0]-bl[0])**2)+((br[1]-bl[1])**2))), int(np.sqrt(((tr[0]-tl[0])**2)+((tr[1]-tl[1])**2))))
            maxH = max(int(np.sqrt(((tr[0]-br[0])**2)+((tr[1]-br[1])**2))), int(np.sqrt(((tl[0]-bl[0])**2)+((tl[1]-bl[1])**2))))
            dst = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype="float32")
            rectified = cv2.warpPerspective(img, cv2.getPerspectiveTransform(rect, dst), (maxW, maxH))

    # PaddleOCR v2.7.3 returns a list of [box, (text, confidence)].
    # We pass cls=True for compatibility; newer versions ignore it.
    # Ref: https://github.com/PaddlePaddle/PaddleOCR/issues/11555
    try:
        result = _ocr_engine.ocr(rectified, cls=True)
    except TypeError:
        result = _ocr_engine.ocr(rectified)

    results = []
    if result and result[0]:
        if isinstance(result[0], dict):
            # PaddleOCR v3.x returns a dict with rec_texts, rec_scores, rec_boxes.
            for text, score, box in zip(result[0].get("rec_texts", []), result[0].get("rec_scores", []), result[0].get("rec_boxes", [])):
                if float(score) >= 0.6:
                    clean = "".join(c for c in text if c.isalnum() or c in ["-", " ", ":"])
                    if len(clean) >= 4:
                        results.append({"bbox": [int(box[0]), int(box[1]), int(box[2]-box[0]), int(box[3]-box[1])], "extracted_text": clean})
        else:
            # PaddleOCR v2.x returns a list of [box, (text, confidence)].
            for line in result[0]:
                box, (text, conf) = line
                if conf >= 0.6:
                    clean = "".join(c for c in text if c.isalnum() or c in ["-", " ", ":"])
                    if len(clean) >= 4:
                        xs, ys = [pt[0] for pt in box], [pt[1] for pt in box]
                        results.append({"bbox": [int(min(xs)), int(min(ys)), int(max(xs)-min(xs)), int(max(ys)-min(ys))], "extracted_text": clean})
    return results
