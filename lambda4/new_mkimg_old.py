# %%
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
News context (Korean):
Headline: {title_kr}
Summary: {summary_kr}

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
        except Exception:
            time.sleep(0.7 * (attempt + 1))

    raise RuntimeError("OpenAI prompt failed")

# =========================================================
# Stability Image Generation (DOUBLE GUARD)
# =========================================================
def generate_image_stability(prompt_en: str, seed: int) -> bytes:
    assert_stability_credit_ok()  # ← 2차 방어

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

    for attempt in range(3):
        try:
            r = requests.post(
                STABILITY_URL,
                headers=headers,
                data=data,
                files=files,
                timeout=90,
            )
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

        except Exception:
            time.sleep(0.7 * (attempt + 1))

    raise RuntimeError("Stability generation failed")

# =========================================================
# S3 / Utils
# =========================================================
def put_png_to_s3(bucket: str, key: str, png_bytes: bytes):
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=png_bytes,
        ContentType="image/png",
        CacheControl="no-cache",
    )

def stable_seed_from_id(article_id: int) -> int:
    h = hashlib.sha256(str(article_id).encode()).hexdigest()
    return int(h[:8], 16)

# =========================================================
# Lambda Handler (GLOBAL HARD BLOCK)
# =========================================================
def lambda_handler(event, context):
    # 🔒 1차 전체 차단
    assert_stability_credit_ok()

    bucket = _env("S3_BUCKET", required=True)
    input_key = _env("INPUT_JSON_KEY", "news/daily/latest.json")
    out_prefix = _env("OUTPUT_IMAGE_PREFIX", "news/images")
    max_images = int(_env("MAX_IMAGES_PER_RUN", "3"))

    data = load_latest_json(bucket, input_key)
    date_str = data.get("date") or datetime.now(KST).date().isoformat()

    articles = data.get("articles", [])
    candidates = [a for a in articles if (a.get("summary") or "").strip()][:max_images]

    results = []
    for a in candidates:
        article_id = a.get("id")
        title = (a.get("title") or "").strip()
        summary = (a.get("summary") or "").strip()
        if not article_id or not title or not summary:
            continue

        prompt = openai_make_prompt(title, summary)
        png = generate_image_stability(prompt, stable_seed_from_id(int(article_id)))

        key = f"{out_prefix}/{date_str}/{article_id}.png"
        put_png_to_s3(bucket, key, png)
        results.append({"id": article_id, "s3_key": key})

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"ok": True, "date": date_str, "count": len(results), "saved": results},
            ensure_ascii=False,
        ),
    }



