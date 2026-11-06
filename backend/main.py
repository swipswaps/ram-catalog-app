import os
import threading
from contextlib import asynccontextmanager
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.rag_engine import query_rag_catalog
from backend.vision_pipeline import init_ocr, process_ram_image, get_ocr_status, get_ocr_error

STATIC_DIR = "/app/static"
os.makedirs(STATIC_DIR, exist_ok=True)

CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "https://swipswaps.github.io,http://localhost:5173").split(",") if o.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load OCR in background to prevent blocking Uvicorn
    threading.Thread(target=init_ocr, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    # Return loading/error state so frontend knows what is happening
    status = get_ocr_status()
    error = get_ocr_error()
    return {
        "status": "ok",
        "ocr_ready": status,
        "ocr_error": error
    }

@app.post("/api/v1/analyze")
async def analyze_and_model(file: UploadFile = File(...)):
    if not get_ocr_status():
        error_msg = get_ocr_error()
        if error_msg:
            raise HTTPException(status_code=500, detail=f"OCR engine crashed: {error_msg}")
        raise HTTPException(status_code=503, detail="OCR engine is still loading models. Please wait.")

    contents = await file.read()
    try:
        ocr_results = process_ram_image(contents)
        extracted_texts = [item["extracted_text"] for item in ocr_results]
        rag_matches = query_rag_catalog(extracted_texts)
        return {"status": "success", "components": rag_matches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
