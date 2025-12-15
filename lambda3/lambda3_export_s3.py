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

def fetch_kst_8am_window(limit=200):
    """
    KST 기준 '08:00~다음날 08:00' 주기 윈도우로
    요약 완료 기사만 가져옴 (article_date 기준)
    """
    now = datetime.now(KST)

    # 오늘 08:00 (KST)
    today_8 = now.replace(hour=8, minute=0, second=0, microsecond=0)

    # 지금이 08:00 이전이면: (어제 08:00 ~ 오늘 08:00)
    if now < today_8:
        start = today_8 - timedelta(days=1)
        end = today_8
        window_date = start.date().isoformat()  # 파일명용(어제 날짜)
    else:
        # 지금이 08:00 이후면: (오늘 08:00 ~ 내일 08:00)
        start = today_8
        end = today_8 + timedelta(days=1)
        window_date = start.date().isoformat()  # 파일명용(오늘 날짜)

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


def lambda_handler(event, context):
    bucket = os.getenv("S3_BUCKET")
    prefix = os.getenv("S3_PREFIX", "news/daily")

    if not bucket:
        return {"statusCode": 500, "body": json.dumps({"ok": False, "error": "S3_BUCKET env missing"}, ensure_ascii=False)}

    rows, date_str, start, end = fetch_kst_8am_window(limit=50)

    # keywords: "a, b, c" -> ["a","b","c"]
    for r in rows:
        kw = (r.get("keywords") or "").strip()
        r["keywords"] = [x.strip() for x in kw.split(",") if x.strip()]

    payload = {
        "date": date_str,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(KST).isoformat(),
        "count": len(rows),
        "articles": rows
    }

    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")


    key_daily = f"{prefix}/{date_str}.json"
    key_latest = f"{prefix}/latest.json"

    for key in (key_daily, key_latest):
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json; charset=utf-8",
            CacheControl="no-cache"
        )

    return {"statusCode": 200, "body": json.dumps({"ok": True, "keys": [key_daily, key_latest], "count": len(rows)}, ensure_ascii=False)}
