import os
import json
import time
import base64
import hashlib
from datetime import datetime, timezone, timedelta

import boto3
import requests

# =========================================================
# Clients / Const
# =========================================================
s3 = boto3.client("s3")
KST = timezone(timedelta(hours=9))

STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"
STABILITY_BALANCE_URL = "https://api.stability.ai/v1/user/balance"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# =========================================================
# Utils
# =========================================================
def _env(name: str, default=None, required=False):
    v = os.getenv(name, default)
    if required and (v is None or str(v).strip() == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def load_latest_json(bucket: str, key: str) -> dict:
    obj = s3.get_object(Bucket=bucket, Key=key)
    raw = obj["Body"].read().decode("utf-8")
    return json.loads(raw)

def s3_exists(bucket: str, key: str) -> bool:
    """
    S3에 이미 같은 key가 존재하면 True
    (이미 생성된 이미지는 절대 재생성하지 않기 위함)
    """
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False

def stable_seed_from_id(article_id: int) -> int:
    h = hashlib.sha256(str(article_id).encode()).hexdigest()
    return int(h[:8], 16)

def get_date_folder(article: dict) -> str:
    """
    S3 폴더명을 안정적으로 만들기 위해:
    - article_date가 있으면 YYYY-MM-DD 사용
    - 없으면 현재 KST 날짜 사용
    """
    ad = (article.get("article_date") or "").strip()
    if len(ad) >= 10:
        return ad[:10]  # "YYYY-MM-DD"
    return datetime.now(KST).date().isoformat()

# =========================================================
# Stability Credit Guard (HARD BLOCK)
# =========================================================
def get_stability_credits() -> float:
    api_key = _env("STABILITY_API_KEY", required=True)
    r = requests.get(
        STABILITY_BALANCE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"[STABILITY_BALANCE_ERROR] {r.status_code}: {r.text}")
    return float(r.json().get("credits", 0))

def assert_stability_credit_ok():
    credits = get_stability_credits()
    if credits <= 0:
        raise RuntimeError(f"[CREDIT_BLOCKED] Stability credits exhausted ({credits})")
    return credits

# =========================================================
# OpenAI Prompt
# =========================================================
def openai_make_prompt(title_kr: str, summary_kr: str) -> str:
    api_key = _env("OPENAI_API_KEY", required=True)
    model = _env("OPENAI_MODEL", "gpt-4o-mini")

    system = (
    "You are an expert visual prompt engineer for photorealistic news images. "
    "Your task is to convert news content into a concrete, realistic visual scene. "
    "Write ONE detailed English prompt paragraph optimized for image generation. "
    "No JSON. No markdown."
)

    user = f"""
Korean headline:
{title_kr}

Korean summary:
{summary_kr}


Task:
Describe a single, specific visual scene that clearly represents the core event of this news.

Guidelines:
- Specify the main subject, environment, action, time of day, and camera angle.
- Use real-world objects, locations, or people implied by the news.
- Avoid abstract concepts unless they are visually concrete.
- No text, captions, logos, or watermarks.
- Photorealistic, cinematic lighting, professional news photography style.
"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": float(_env("OPENAI_TEMPERATURE", "0.2")),
        "max_tokens": int(_env("OPENAI_MAX_TOKENS", "220")),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(3):
        try:
            r = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"[OPENAI_ERROR] {r.status_code}: {r.text[:300]}")
            return r.json()["choices"][0]["message"]["content"].strip()[:1200]
        except Exception as e:
            print(f"[OPENAI] attempt={attempt+1} failed: {e}")
            time.sleep(0.7 * (attempt + 1))

    raise RuntimeError("OpenAI prompt failed")

# =========================================================
# Stability Image Generation
# =========================================================
def generate_image_stability(prompt_en: str, seed: int) -> bytes:
    api_key = _env("STABILITY_API_KEY", required=True)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    data = {
        "prompt": prompt_en,
        "output_format": "png",
        "cfg_scale": float(_env("STABILITY_CFG_SCALE", "6.0")),
        "steps": int(_env("STABILITY_STEPS", "28")),
        "aspect_ratio": _env("STABILITY_ASPECT_RATIO", "16:9"),
        "style_preset": _env("STABILITY_STYLE", "photographic"),
        "seed": str(seed),
    }

    files = {"none": ""}

    last_err = None
    for attempt in range(3):
        try:
            r = requests.post(
                STABILITY_URL,
                headers=headers,
                data=data,
                files=files,
                timeout=90,
            )

            # 402면 여기서 바로 실패(크레딧 부족)
            if r.status_code == 402:
                raise RuntimeError(f"[STABILITY_ERROR] 402: {r.text[:300]}")

            if r.status_code != 200:
                raise RuntimeError(f"[STABILITY_ERROR] {r.status_code}: {r.text[:300]}")

            ct = (r.headers.get("Content-Type") or "").lower()
            if "application/json" in ct:
                payload = r.json()
                b64 = (
                    payload.get("image")
                    or (payload.get("artifacts") or [{}])[0].get("base64")
                )
                if b64:
                    return base64.b64decode(b64)

            if "image/png" in ct or r.content[:8] == b"\x89PNG\r\n\x1a\n":
                return r.content

            raise RuntimeError("Unknown Stability response")

        except Exception as e:
            last_err = e
            print(f"[STABILITY] attempt={attempt+1} failed: {e}")
            time.sleep(0.7 * (attempt + 1))

    raise RuntimeError(f"Stability generation failed: {last_err}")

# =========================================================
# S3 Put
# =========================================================
def put_png_to_s3(bucket: str, key: str, png_bytes: bytes):
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=png_bytes,
        ContentType="image/png",
        CacheControl="no-cache",
    )

# =========================================================
# Lambda Handler
# =========================================================
def lambda_handler(event, context):
    # 🔒 전체 실행 전에 크레딧 1회만 체크 (중복 호출 제거)
    credits = assert_stability_credit_ok()
    print(f"[CREDITS] Stability credits available: {credits}")

    bucket = _env("S3_BUCKET", required=True)
    input_key = _env("INPUT_JSON_KEY", "news/daily/latest.json")
    out_prefix = _env("OUTPUT_IMAGE_PREFIX", "news/images")
    max_images = int(_env("MAX_IMAGES_PER_RUN", "3"))

    data = load_latest_json(bucket, input_key)
    articles = data.get("articles", [])

    # 요약문 있는 기사만 대상
    candidates = [a for a in articles if (a.get("summary") or "").strip()]

    results = []
    skipped = 0
    tried = 0

    for a in candidates:
        if len(results) >= max_images:
            break

        article_id = a.get("id")
        title = (a.get("title") or "").strip()
        summary = (a.get("summary") or "").strip()

        if not article_id or not title or not summary:
            continue

        date_folder = get_date_folder(a)
        key = f"{out_prefix}/{date_folder}/{article_id}.png"

        # ✅ 재생성 방지: 이미 있으면 스킵 (OpenAI/Stable 호출 전에!)
        if s3_exists(bucket, key):
            skipped += 1
            results.append({"id": article_id, "s3_key": key, "skipped": True})
            print(f"[SKIP] already exists: s3://{bucket}/{key}")
            continue

        tried += 1
        try:
            prompt = openai_make_prompt(title, summary)
            png = generate_image_stability(prompt, stable_seed_from_id(int(article_id)))

            put_png_to_s3(bucket, key, png)
            results.append({"id": article_id, "s3_key": key, "skipped": False})
            print(f"[SAVED] s3://{bucket}/{key}")

        except Exception as e:
            # 실패해도 전체 Lambda는 계속 돌게
            print(f"[ERROR] id={article_id} generate failed: {e}")
            results.append({"id": article_id, "error": str(e), "skipped": False})

    date_str = datetime.now(KST).date().isoformat()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "ok": True,
                "date": date_str,
                "max_images": max_images,
                "attempted": tried,
                "skipped_existing": skipped,
                "count": len([r for r in results if r.get("s3_key") and not r.get("skipped")]),
                "results": results,
            },
            ensure_ascii=False,
        ),
    }
