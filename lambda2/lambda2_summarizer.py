# lambda2_summarizer.py

import os
import json

from llm_summary import summarize_article, parse_summary_output
from db_module import (
    fetch_unsummarized_articles,
    insert_news_ai_meta,
    mark_article_summarized,
)


def process_one_article(article: dict):
    """
    기사 1개에 대해:
    - 요약 생성
    - summary/keywords 파싱
    - topic = category 로 설정
    - news_ai_meta에 저장
    - 원본 기사 is_summarized = 1 로 변경
    """
    article_id = article["id"]
    title = article["title"]
    content = article["content"]
    category = article.get("category", "")

    print(f"[Lambda2] 기사 요약 시작 - id={article_id}, 제목={title[:30]}...")

    # 1) LLM 요약 호출
    raw = summarize_article(title, content)

    # 2) 파싱
    summary, keywords = parse_summary_output(raw)

    # 3) topic = category (지금은 이렇게 사용)
    topic = category

    # 4) 메타 테이블에 INSERT
    insert_news_ai_meta(article_id, summary, topic, keywords)
``
    # 5) 원본 기사 플래그 변경
    mark_article_summarized(article_id)

    print(f"[Lambda2] 요약 완료 - article_id={article_id}")


def lambda_handler(event=None, context=None):
    """
    Lambda #2 엔트리 포인트 (로컬에서도 이걸 호출)
    - 요약 안 된 기사들 가져와서 최대 N개만 처리
    """
    max_count = int(os.getenv("MAX_SUMMARY_PER_RUN", "10"))  # 한 번에 10개만

    print(f"[Lambda2] 시작 - 최대 {max_count}개 기사 요약 예정")

    articles = fetch_unsummarized_articles(limit=max_count)
    print(f"[Lambda2] 요약 대상 기사 수: {len(articles)}")

    processed = 0

    for article in articles:
        try:
            process_one_article(article)
            processed += 1
        except Exception as e:
            print(f"[Lambda2] 요약 중 오류 - article_id={article['id']}, error={e}")

    result = {
        "message": "요약 Lambda 실행 완료",
        "processed": processed,
        "target": max_count,
    }

    print(f"[Lambda2] 최종 처리 개수: {processed}/{max_count}")

    return {
        
        "statusCode": 200,
        "body": json.dumps(result, ensure_ascii=False),
    }


if __name__ == "__main__":
    print("[Local] lambda2_summarizer.py 직접 실행 시작")
    resp = lambda_handler()
    print("[Local] 실행 결과:", resp)
