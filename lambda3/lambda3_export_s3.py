import os, json
import boto3
import mysql.connector
from datetime import datetime, timezone, timedelta

s3 = boto3.client("s3")
KST = timezone(timedelta(hours=9))


def get_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def fetch_kst_8am_window_summarized(limit=200):
    """
    KST 기준 08:00 ~ 다음날 08:00 윈도우에서 '요약 완료' 기사만 가져옴
    기준: article_date
    """
    now = datetime.now(KST)
    today_8 = now.replace(hour=8, minute=0, second=0, microsecond=0)

    if now < today_8:
        start = today_8 - timedelta(days=1)
        end = today_8
        window_date = start.date().isoformat()
    else:
        start = today_8
        end = today_8 + timedelta(days=1)
        window_date = start.date().isoformat()

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    sql = """
    SELECT
      a.id, a.title, a.category, a.article_date, a.url,
      m.summary, m.keywords
    FROM news_articles a
    LEFT JOIN news_ai_meta m ON m.article_id = a.id
    WHERE a.is_summarized = 1
      AND a.article_date >= %s AND a.article_date < %s
    ORDER BY a.article_date DESC, a.id DESC
    LIMIT %s
    """

    cur.execute(sql, (
        start.strftime("%Y-%m-%d %H:%M:%S"),
        end.strftime("%Y-%m-%d %H:%M:%S"),
        limit
    ))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows, window_date, start, end


def load_existing_json(bucket: str, key: str) -> dict:
    """
    S3에 파일이 없으면 빈 구조로 반환
    """
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        raw = obj["Body"].read().decode("utf-8")
        return json.loads(raw)
    except s3.exceptions.NoSuchKey:
        return {}
    except Exception:
        # JSON 깨짐/권한 등 어떤 이유든 일단 빈값으로
        return {}


def normalize_rows(rows: list[dict]) -> list[dict]:
    """
    keywords: "a, b, c" -> ["a","b","c"]
    datetime -> 문자열로 변환 (json serialize 안정화)
    """
    out = []
    for r in rows:
        rr = dict(r)

        # article_date가 datetime이면 문자열로
        if isinstance(rr.get("article_date"), datetime):
            rr["article_date"] = rr["article_date"].strftime("%Y-%m-%d %H:%M:%S")

        kw = (rr.get("keywords") or "").strip()
        rr["keywords"] = [x.strip() for x in kw.split(",") if x.strip()]

        out.append(rr)
    return out


def merge_feed(existing_articles: list[dict], new_articles: list[dict], max_items: int = 1000) -> list[dict]:
    """
    latest.json을 누적 피드로 만들기:
    - id(없으면 url) 기준 중복 제거
    - 새 데이터가 우선
    - 최신순 정렬
    - 최대 max_items까지만 유지
    """
    by_key = {}

    def key_of(a: dict) -> str:
        return str(a.get("id") or a.get("url") or "")

    # 기존 먼저
    for a in existing_articles or []:
        k = key_of(a)
        if k:
            by_key[k] = a

    # 새 데이터로 덮어쓰기 (최신 데이터 우선)
    for a in new_articles or []:
        k = key_of(a)
        if k:
            by_key[k] = a

    merged = list(by_key.values())

    # article_date: "YYYY-MM-DD HH:MM:SS" 형태면 문자열 정렬로도 최신순 OK
    merged.sort(key=lambda x: (x.get("article_date") or ""), reverse=True)

    return merged[:max_items]


def lambda_handler(event, context):
    bucket = os.getenv("S3_BUCKET")
    prefix = os.getenv("S3_PREFIX", "news/daily")
    limit = int(os.getenv("EXPORT_LIMIT", "200"))          # 윈도우에서 가져올 최대 기사 수
    feed_max = int(os.getenv("FEED_MAX_ITEMS", "1000"))   # latest.json 누적 최대 개수

    if not bucket:
        return {"statusCode": 500, "body": json.dumps({"ok": False, "error": "S3_BUCKET env missing"}, ensure_ascii=False)}

    # 1) DB에서 “KST 08시 윈도우” 요약 완료 기사 가져오기
    rows, date_str, start, end = fetch_kst_8am_window_summarized(limit=limit)
    rows = normalize_rows(rows)

    # 2) 날짜별 스냅샷 파일(영구 누적)
    payload_daily = {
        "date": date_str,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(KST).isoformat(),
        "count": len(rows),
        "articles": rows
    }
    body_daily = json.dumps(payload_daily, ensure_ascii=False).encode("utf-8")

    key_daily = f"{prefix}/{date_str}.json"
    s3.put_object(
        Bucket=bucket,
        Key=key_daily,
        Body=body_daily,
        ContentType="application/json; charset=utf-8",
        CacheControl="no-cache"
    )

    # 3) latest.json = “누적 피드” (매번 merge해서 계속 쌓기)
    key_latest = f"{prefix}/latest.json"
    existing = load_existing_json(bucket, key_latest)
    existing_articles = existing.get("articles", []) if isinstance(existing, dict) else []

    merged_articles = merge_feed(existing_articles, rows, max_items=feed_max)

    payload_latest = {
        "generated_at": datetime.now(KST).isoformat(),
        "count": len(merged_articles),
        "articles": merged_articles
    }
    body_latest = json.dumps(payload_latest, ensure_ascii=False).encode("utf-8")

    s3.put_object(
        Bucket=bucket,
        Key=key_latest,
        Body=body_latest,
        ContentType="application/json; charset=utf-8",
        CacheControl="no-cache"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "ok": True,
            "keys": [key_daily, key_latest],
            "daily_count": len(rows),
            "feed_count": len(merged_articles),
            "window": {"start": start.isoformat(), "end": end.isoformat()}
        }, ensure_ascii=False)
    }
