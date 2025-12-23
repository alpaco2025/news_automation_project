import os
import json
import re
from datetime import datetime, timezone, timedelta

import boto3

KST = timezone(timedelta(hours=9))

s3 = boto3.client("s3")
polly = boto3.client("polly")


def _env(name: str, default=None, required: bool = False):
    v = os.getenv(name, default)
    if required and (v is None or str(v).strip() == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return v


# 자주 나오는 약어/영문 발음 보정(원하면 계속 추가)
PRON_MAP = {
    "GPU": "지피유",
    "CPU": "씨피유",
    "AI": "에이아이",
    "LLM": "엘엘엠",
    "API": "에이피아이",
    "OpenAI": "오픈에이아이",
    "AWS": "에이더블유에스",
    "NVIDIA": "엔비디아",
}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"\s+", " ", t)
    # Polly 입력 너무 길어지는 것 방지(요약은 짧지만 안전장치)
    return t[:1200]


def to_ssml(summary: str) -> str:
    t = normalize_text(summary)

    # SSML escape
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 발음 교정
    for k, alias in PRON_MAP.items():
        t = t.replace(k, f'<sub alias="{alias}">{k}</sub>')

    # “오늘의 기사” 같은 멘트도 가능(원하면 문구 바꿔)
    return f"<speak>요약입니다. <break time='200ms'/> {t}</speak>"


def s3_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def load_json_from_s3(bucket: str, key: str) -> dict:
    obj = s3.get_object(Bucket=bucket, Key=key)
    raw = obj["Body"].read().decode("utf-8")
    return json.loads(raw)


def put_mp3(bucket: str, key: str, mp3_bytes: bytes):
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=mp3_bytes,
        ContentType="audio/mpeg",
        CacheControl="no-cache",
    )


def synthesize_mp3(summary: str) -> bytes:
    voice_id = _env("POLLY_VOICE_ID", "Seoyeon")
    engine = _env("POLLY_ENGINE", "standard")  # 가능하면 neural
    ssml = to_ssml(summary)

    resp = polly.synthesize_speech(
        Text=ssml,
        TextType="ssml",
        OutputFormat="mp3",
        VoiceId=voice_id,
        Engine=engine,
    )

    stream = resp.get("AudioStream")
    if not stream:
        raise RuntimeError("Polly returned no AudioStream")
    return stream.read()


def get_date_folder(article: dict, fallback_date: str) -> str:
    # article_date: "2025-12-16 19:21:00" → "2025-12-16"
    ad = (article.get("article_date") or "").strip()
    if len(ad) >= 10:
        return ad[:10]

    d = (article.get("date") or "").strip()
    if len(d) >= 10:
        return d[:10]

    return fallback_date or datetime.now(KST).strftime("%Y-%m-%d")


def lambda_handler(event, context):
    bucket = _env("S3_BUCKET", required=True)

    # 람다3가 만들어둔 JSON을 읽는다
    input_key = _env("INPUT_JSON_KEY", "news/daily/latest.json")

    # mp3 저장 경로
    tts_prefix = _env("TTS_PREFIX", "news/tts")

    # 한 번 실행 시 생성할 최대 mp3 수
    max_per_run = int(_env("MAX_TTS_PER_RUN", "20"))

    # 이미 mp3 있으면 스킵
    skip_if_exists = _env("SKIP_IF_S3_EXISTS", "1") == "1"

    data = load_json_from_s3(bucket, input_key)
    fallback_date = (data.get("date") or "").strip()

    articles = data.get("articles", []) or []

    # summary 있는 것만
    candidates = [a for a in articles if (a.get("summary") or "").strip()]
    candidates = candidates[:max_per_run]

    saved = []
    skipped = 0
    failed = 0

    for a in candidates:
        article_id = a.get("id")
        summary = (a.get("summary") or "").strip()

        if not article_id or not summary:
            failed += 1
            continue

        date_str = get_date_folder(a, fallback_date)
        out_key = f"{tts_prefix}/{date_str}/{article_id}.mp3"

        if skip_if_exists and s3_exists(bucket, out_key):
            skipped += 1
            continue

        try:
            mp3 = synthesize_mp3(summary)
            put_mp3(bucket, out_key, mp3)
            saved.append({"id": article_id, "s3_key": out_key})
        except Exception as e:
            failed += 1
            print(f"[TTS] failed id={article_id} err={e}")

    result = {
        "ok": True,
        "input_key": input_key,
        "target_count": len(candidates),
        "saved_count": len(saved),
        "skipped_count": skipped,
        "failed_count": failed,
        "saved": saved[:20],
    }

    return {"statusCode": 200, "body": json.dumps(result, ensure_ascii=False)}
