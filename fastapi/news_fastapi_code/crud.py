# crud.py
from sqlalchemy import text
from db import engine

SEARCH_SQL = """
SELECT
  a.id AS article_id,
  a.title,
  a.category,
  DATE(a.article_date) AS article_date,
  DATE(m.created_at) AS asset_date,
  a.url,
  m.summary,
  m.keywords
FROM news_articles a
JOIN news_ai_meta m ON m.article_id = a.id
WHERE a.is_summarized = 1
  AND (
    LOWER(a.title) LIKE LOWER(:q)
    OR LOWER(COALESCE(m.summary, '')) LIKE LOWER(:q)
    OR LOWER(COALESCE(m.keywords, '')) LIKE LOWER(:q)
  )
ORDER BY a.article_date DESC, a.id DESC
LIMIT 100
"""
def search_articles(query: str):
    q = f"%{query}%"

    with engine.connect() as conn:
        rows = conn.execute(
            text(SEARCH_SQL),
            {"q": q}
        ).mappings().all()

    return rows