===============================================================================
RAM CATALOG & PARAMETRIC CAD SYSTEM
DDR3 / DDR4 / DDR5 COMPONENT IDENTIFICATION
===============================================================================

1. HOW WE GOT HERE
------------------
High-density memory modules require JEDEC signal-integrity control
(JESD79-3D, JESD79-4, JESD79-5) and controlled-impedance PCB manufacturing.
Manual FBGA rework from donor sticks is economically unviable: thermal
delamination and sub-1 ps length-matching budgets make it a >40% failure
process. This repository ports the receipts-ocr / receipts-ocr-rag
architecture to IC package segmentation, part-number OCR, JEDEC vendor
lookup, and procedural 3D CAD generation via CadQuery.

2. WHERE WE ARE
---------------
Static frontend (Vite + React + Three.js) on GitHub Pages.
Containerized backend (FastAPI + OpenCV + Tesseract + FAISS + CadQuery)
on any HTTPS container host.

3. HOW TO USE
-------------
Local:
  docker compose up --build -d
  npm install
  npm run dev
  open http://localhost:5173

Production frontend:
  gh variable set VITE_BACKEND_URL --body "https://your-backend.example.com"
  Push to main. The workflow builds dist/ and deploys with SPA fallback.

Production backend:
  Build Dockerfile.backend and deploy to an HTTPS container host.
  Set CORS_ORIGINS to the GitHub Pages origin.

4. ENVIRONMENT VARIABLES
------------------------
VITE_BACKEND_URL   Repository variable (frontend build time)
CORS_ORIGINS       Backend runtime (comma-separated)
DB_PATH            Backend runtime (default /app/ram_catalog.db)

5. CREDITS
----------
CadQuery: https://cadquery.readthedocs.io/
CadQuery GLTF issue #1508: https://github.com/CadQuery/cadquery/issues/1508
OpenCV: https://opencv.org/
Tesseract: https://github.com/tesseract-ocr/tesseract
FAISS: https://github.com/facebookresearch/faiss
Sentence-Transformers: https://www.sbert.net/
Awesome Open Source Hardware: https://github.com/aolofsson/awesome-opensource-hardware
===============================================================================
