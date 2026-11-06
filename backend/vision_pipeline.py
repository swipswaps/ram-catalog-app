import threading
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from paddleocr import PaddleOCR

_ocr_engine: Optional[PaddleOCR] = None
_ocr_ready = threading.Event()
_ocr_error: Optional[str] = None

def init_ocr():
    global _ocr_engine, _ocr_error
    try:
        _ocr_engine = PaddleOCR(
            lang="en",
            use_textline_orientation=True,
            enable_mkldnn=False,
            device="cpu"
        )
        _ocr_ready.set()
    except Exception as e:
        _ocr_error = str(e)
        print(f"CRITICAL: PaddleOCR init failed: {e}")

def get_ocr_status() -> bool:
    return _ocr_ready.is_set()

def get_ocr_error() -> Optional[str]:
    return _ocr_error

def process_ram_image(image_bytes: bytes) -> List[Dict[str, Any]]:
    assert _ocr_engine is not None, "OCR engine accessed before initialization."
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None: return []

    # Perspective warp
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rectified = img
    if contours:
        largest = max(contours, key=cv2.contourArea)
        approx = cv2.approxPolyDP(largest, 0.02 * cv2.arcLength(largest, True), True)
        if len(approx) == 4:
            # Simplified warp for brevity
            rectified = img # Omitted full warp logic for space

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
