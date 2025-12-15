# run_crawl_and_save.py

from crawler_adapter import get_articles_for_db
from db_module import insert_articles


def main():
    # 1) 크롤링 + 전처리 + 어댑터 정리
    target_count = 50  # 테스트로 50개 정도
    articles = get_articles_for_db(target_count=target_count)

    print(f"✅ 크롤링 + 전처리된 기사 수: {len(articles)}")

    if not articles:
        print("⚠️ 가져온 기사가 없습니다. 크롤러 로직을 확인해 주세요.")
        return

    # 2) 샘플 1개만 출력해서 구조 확인
    sample = articles[0]
    print("\n=== 샘플 기사 1개 ===")
    print("URL:", sample.get("url"))
    print("제목:", sample.get("title"))
    print("카테고리:", sample.get("category"))
    print("발행일(article_date):", sample.get("article_date"))
    print("source:", sample.get("source"))
    print("====================\n")

    # 3) DB에 저장
    insert_articles(articles)


if __name__ == "__main__":
    main()
