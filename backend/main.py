import os
import threading
from contextlib import asynccontextmanager
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.cad_engine import generate_ram_cad_model
from backend.database import init_db, store_scan
from backend.rag_engine import query_rag_catalog
from backend.vision_pipeline import init_ocr, process_ram_image, get_ocr_status

STATIC_DIR = "/app/static"
CAD_DIR = os.path.join(STATIC_DIR, "cad")
os.makedirs(CAD_DIR, exist_ok=True)

# Gate: Static directory must exist for FastAPI mounting.
# Explanation: FastAPI's StaticFiles will throw a RuntimeError if the directory
# is missing. os.makedirs ensures the mount succeeds.
# Ref: https://fastapi.tiangolo.com/tutorial/static-files/
assert os.path.exists(STATIC_DIR), f"Static directory {STATIC_DIR} must exist."

CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "https://swipswaps.github.io,http://localhost:5173").split(",") if o.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Gate: Load OCR in a background thread to prevent Fly.io 60s timeout.
    # Explanation: Fly.io caps health check grace periods at 60s. PaddleOCR
    # loading can take >60s. Blocking Uvicorn prevents port binding, causing
    # Fly to kill the machine.
    # Ref: https://community.fly.io/t/cold-start-and-health-check-failures-on-deployed-apis-repost/18523
    threading.Thread(target=init_ocr, daemon=True).start()
    yield

app = FastAPI(title="RAM Engine", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/analyze")
async def analyze_and_model(file: UploadFile = File(...)):
    # Gate: OCR engine must be ready before processing.
    # Explanation: Returns 503 if background thread hasn't finished loading.
    if not get_ocr_status():
        raise HTTPException(status_code=503, detail="OCR engine is still loading. Please try again in a moment.")
    
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    form_factor = "DIMM"
    if img is not None:
        h, w = img.shape[:2]
        if w / h < 3.5:
            form_factor = "SODIMM"
            
    ocr_results = process_ram_image(contents)
    extracted_texts = [item["extracted_text"] for item in ocr_results]
    rag_matches = query_rag_catalog(extracted_texts)
    cad_path = generate_ram_cad_model(module_type="DDR4", ic_count=len(extracted_texts) or 8, form_factor=form_factor)
    store_scan(file.filename, rag_matches, cad_path)
    return {"status": "success", "components": rag_matches, "cad_model_url": cad_path}
