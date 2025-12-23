# db_module.py
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# .env 파일 불러오기
load_dotenv()

def get_connection():
    """
    .env에 설정한 DB_HOST, DB_USER, DB_PASSWORD, DB_NAME으로
    MySQL 커넥션을 만들어서 리턴하는 함수
    """
def get_connection():
    """
    .env에 설정한 값으로 MySQL 커넥션 생성
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3306")),  # ← 포트 추가 (기본 3306)
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        if conn.is_connected():
            print("✅ DB 연결 성공")
        return conn
    except Error as e:
        print("❌ DB 연결 실패:", e)
        return None



def insert_articles(articles: list[dict]):
    """
    기사 딕셔너리 리스트를 news_articles 테이블에 INSERT 하는 함수
    (지금은 테스트용으로만 쓸 거라, 나중에 전처리 결과랑 연결하면 됨)
    """
    conn = get_connection()
    if conn is None:
        print("DB 연결 실패로 INSERT 불가")
        return

    sql = """
    INSERT INTO news_articles
    (url, title, content, article_date, source, category)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        title = VALUES(title),
        content = VALUES(content),
        article_date = VALUES(article_date),
        source = VALUES(source),
        category = VALUES(category)
    """

    cur = conn.cursor()

    for a in articles:
        cur.execute(sql, (
            a["url"],
            a["title"],
            a["content"],
            a["article_date"],
            a["source"],
            a["category"],
        ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ 총 {len(articles)}개 기사 INSERT 완료")


# 이 파일을 직접 실행했을 때만 테스트 해보는 용도
if __name__ == "__main__":
    from datetime import datetime

    sample_articles = [
        {
            "url": "https://test.com/article1",
            "title": "테스트 기사 1",
            "content": "이것은 테스트 본문입니다.",
            "article_date": datetime.now(),
            "source": "AITimes",
            "category": "테스트"
        }
    ]

    insert_articles(sample_articles)