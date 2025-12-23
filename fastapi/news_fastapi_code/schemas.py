# schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date


class Article(BaseModel):
    article_id: int
    title: str
    category: Optional[str]
    article_date: datetime
    asset_date: Optional[date]   # LEFT JOIN 대비
    url: str
    summary: Optional[str]
    keywords: Optional[str]


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[Article]
