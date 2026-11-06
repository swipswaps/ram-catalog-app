import threading
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from paddleocr import PaddleOCR

_ocr_engine: Optional[PaddleOCR] = None
_ocr_ready = threading.Event()

def init_ocr():
    global _ocr_engine
    try:
        # PaddleOCR v3 constructor. show_log removed, use_angle_cls deprecated.
        # Ref: https://wenku.csdn.net/answer/3ek27u35ozs1
        _ocr_engine = PaddleOCR(
            lang="en",
            use_textline_orientation=True,
            enable_mkldnn=False,
            device="cpu"
        )
        _ocr_ready.set()
    except Exception as e:
        print(f"Failed to initialize PaddleOCR: {e}")

def get_ocr_status() -> bool:
    return _ocr_ready.is_set()

def process_ram_image(image_bytes: bytes) -> List[Dict[str, Any]]:
    # Gate: OCR engine must be initialized.
    # Explanation: Calling .predict() on an uninitialized engine raises AttributeError.
    assert _ocr_engine is not None, "OCR engine accessed before initialization."
    
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
            rect = np.zeros((4, 2), dtype="float32")
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]
            rect[2] = pts[np.argmax(s)]
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]
            rect[3] = pts[np.argmax(diff)]
            (tl, tr, br, bl) = rect
            maxW = max(int(np.sqrt(((br[0]-bl[0])**2)+((br[1]-bl[1])**2))), int(np.sqrt(((tr[0]-tl[0])**2)+((tr[1]-tl[1])**2))))
            maxH = max(int(np.sqrt(((tr[0]-br[0])**2)+((tr[1]-br[1])**2))), int(np.sqrt(((tl[0]-bl[0])**2)+((tl[1]-bl[1])**2))))
            dst = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype="float32")
            rectified = cv2.warpPerspective(img, cv2.getPerspectiveTransform(rect, dst), (maxW, maxH))

    # PaddleOCR v3 uses .predict() over .ocr(). Returns a list of dicts.
    # Ref: https://github.com/PaddlePaddle/PaddleOCR/issues/11555
    result = _ocr_engine.predict(rectified)

    results = []
    if result and len(result) > 0:
        res_dict = result[0]
        texts = res_dict.get("rec_texts", [])
        scores = res_dict.get("rec_scores", [])
        boxes = res_dict.get("rec_boxes", [])
        for text, score, box in zip(texts, scores, boxes):
            if score >= 0.6:
                clean = "".join(c for c in text if c.isalnum() or c in ["-", " ", ":"])
                if len(clean) >= 4:
                    results.append({"bbox": [int(box[0]), int(box[1]), int(box[2]-box[0]), int(box[3]-box[1])], "extracted_text": clean})
    return results
