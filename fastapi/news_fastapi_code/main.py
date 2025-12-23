# main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from schemas import SearchResponse
from crud import search_articles

app = FastAPI(
    title="News Search API",
    version="1.1.0"
)

# =========================
# CORS 설정
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://alpaco2025.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =========================
# Search API
# =========================
@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="검색어", min_length=1, max_length=50)
):
    q = q.strip()
    results = search_articles(q)

    return {
        "query": q,
        "count": len(results),
        "results": results
    }