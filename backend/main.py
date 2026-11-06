import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.cad_engine import generate_ram_cad_model
from backend.database import init_db, store_scan
from backend.rag_engine import query_rag_catalog
from backend.vision_pipeline import process_ram_image

STATIC_DIR = "/app/static"
CAD_DIR = os.path.join(STATIC_DIR, "cad")
os.makedirs(CAD_DIR, exist_ok=True)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "https://swipswaps.github.io,http://localhost:5173",
    ).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="RAM OCR, RAG & 3D CAD Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/analyze")
async def analyze_and_model(file: UploadFile = File(...)):
    contents = await file.read()
    ocr_results = process_ram_image(contents)
    extracted_texts = [item["extracted_text"] for item in ocr_results]
    rag_matches = query_rag_catalog(extracted_texts)
    ic_count = len(extracted_texts) if extracted_texts else 8
    cad_path = generate_ram_cad_model(module_type="DDR4", ic_count=ic_count)
    store_scan(file.filename, rag_matches, cad_path)
    return {"status": "success", "components": rag_matches, "cad_model_url": cad_path}
