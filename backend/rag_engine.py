from typing import Any, Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from backend.vendor_chips import DDR_VENDOR_DATABASE, lookup_vendor_chip

_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
_DIM = 384
_INDEX = faiss.IndexFlatIP(_DIM)
_KNOWN_PARTS = list(DDR_VENDOR_DATABASE.keys())
_EMBEDDINGS = _MODEL.encode(_KNOWN_PARTS).astype("float32")
faiss.normalize_L2(_EMBEDDINGS)
_INDEX.add(_EMBEDDINGS)


def query_rag_catalog(extracted_texts: List[str]) -> List[Dict[str, Any]]:
    matched: List[Dict[str, Any]] = []
    for text in extracted_texts:
        spec = lookup_vendor_chip(text)
        if spec is not None:
            matched.append(
                {
                    "queried_token": text,
                    "match_type": "EXACT_JEDEC",
                    "specification": spec.model_dump(),
                    "smt_compatibility": "APPROVED",
                }
            )
            continue

        query_vec = _MODEL.encode([text]).astype("float32")
        faiss.normalize_L2(query_vec)
        scores, indices = _INDEX.search(query_vec, k=1)
        best_idx = int(indices[0][0])
        cosine_score = float(scores[0][0])

        if cosine_score >= 0.75:
            matched_part = _KNOWN_PARTS[best_idx]
            matched.append(
                {
                    "queried_token": text,
                    "match_type": "VECTOR_SIMILARITY",
                    "matched_part": matched_part,
                    "cosine_similarity": round(cosine_score, 4),
                    "specification": DDR_VENDOR_DATABASE[matched_part].model_dump(),
                    "smt_compatibility": "REVIEW_REQUIRED",
                }
            )
        else:
            matched.append(
                {
                    "queried_token": text,
                    "match_type": "UNKNOWN",
                    "specification": None,
                    "smt_compatibility": "MANUAL_INSPECTION_REQUIRED",
                }
            )
    return matched
