from typing import List, Dict

from aitimes_crawler import crawl_articles

def get_articles_for_db(target_count:int = 50):
    raw_articles = crawl_articles(target_count = target_count)

    cleaned_articles : list[dict] = []

    for a in raw_articles:
        try:
            cleaned_articles.append({
                "url": a["url"].strip(),
                "category": a.get("category", "").strip(),
                "title": a.get("title", "").strip(),
                "content": a.get("content", "").strip(),
                "article_date": a.get("article_date", None),  # datetime 그대로 유지
                "source": a.get("source", "AITimes"),
            })
        except Exception as e:
            print("어댑터 정리 중 오류 발생 -> {e}")
            continue

    
    return cleaned_articles