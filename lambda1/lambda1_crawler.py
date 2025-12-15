# lambda1_crawler.py

import os
import json
from crawler_adapter import get_articles_for_db
from db_module import insert_articles


def lambda_handler(event=None, context=None):
    """
    Lambda #1 역할:
    - 기사 크롤링 + 전처리
    - DB 저장
    """

    # 환경변수에서 개수 가져오기 (없으면 기본 50)
    target_count = int(os.getenv("TARGET_COUNT", "50"))

    print(f"[Lambda] 시작 - target_count = {target_count}")

    # 1) 크롤링 + 전처리 + 어댑터 정리
    articles = get_articles_for_db(target_count=target_count)
    print(f"[Lambda] 크롤링 완료 → {len(articles)}개 기사 수집")

    if not articles:
        msg = "가져온 기사가 없습니다."
        print("[Lambda] " + msg)
        result = {"message": msg, "count": 0}
    else:
        # 2) DB 저장
        insert_articles(articles)
        result = {"message": "크롤링 & DB 저장 완료", "count": len(articles)}
        print(f"[Lambda] DB 저장 완료 → {len(articles)}개")

    # Lambda 리턴 형식 흉내
    return {
        "statusCode": 200,
        "body": json.dumps(result, ensure_ascii=False)
    }

