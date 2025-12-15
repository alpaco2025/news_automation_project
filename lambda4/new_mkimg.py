import os
import json
import time
import base64
import hashlib
from datetime import datetime, timezone, timedelta

import boto3
import requests

s3 = boto3.client("s3")
KST = timezone(timedelta(hours=9))

STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

def _env(name: str, default=None, required=False):
    v = os.getenv(name, default)
    if required and (v is None or str(v).strip() == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def load_latest_json(bucket: str, key: str) -> dict:
    obj = s3.get_object(Bucket=bucket, Key=key)
    raw = obj["Body"].read().decode("utf-8")
    return json.loads(raw)

def openai_make_prompt(title_kr: str, summary_kr: str) -> str:
    api_key = _env("OPENAI_API_KEY", required=True)
    model = _env("OPENAI_MODEL", "gpt-4o-mini")

    system = (
        "You are a prompt engineer for generating photorealistic news thumbnail images. "
        "Write a single English prompt optimized for image generation. "
        "No JSON. No markdown. One paragraph only."
    )
    user = f"""
Korean headline:
{title_kr}

Korean summary:
{summary_kr}

Requirements:
- Output: ONE English prompt paragraph for a professional news thumbnail.
- Photorealistic, cinematic lighting, clean composition, symbolic but accurate.
- Avoid text/captions/logos/watermarks.
- If people appear: realistic anatomy, normal hands, no extra limbs.
- Keep it concise but specific.
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

    last_err = None
    for attempt in range(3):
        try:
            r = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"[OPENAI_ERROR] {r.status_code}: {r.text[:300]}")
            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()
            return text[:1200]
        except Exception as e:
            last_err = e
            time.sleep(0.7 * (attempt + 1))
    raise RuntimeError(f"OpenAI prompt failed: {last_err}")

def generate_image_stability(prompt_en: str, seed: int) -> bytes:
    stability_key = _env("STABILITY_API_KEY", required=True)

    headers = {
        "Authorization": f"Bearer {stability_key}",
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
            r = requests.post(STABILITY_URL, headers=headers, data=data, files=files, timeout=90)
            if r.status_code != 200:
                raise RuntimeError(f"[STABILITY_ERROR] {r.status_code}: {r.text[:500]}")

            ct = (r.headers.get("Content-Type") or "").lower()
            if "application/json" in ct:
                payload = r.json()
                if "image" in payload:
                    return base64.b64decode(payload["image"])
                if "artifacts" in payload and payload["artifacts"]:
                    b64 = payload["artifacts"][0].get("base64")
                    if b64:
                        return base64.b64decode(b64)
                raise RuntimeError(f"[INVALID_STABILITY_JSON] keys={list(payload.keys())}")

            # binary png
            if "image/png" in ct or r.content[:8] == b"\x89PNG\r\n\x1a\n":
                return r.content

            raise RuntimeError(f"[UNKNOWN_STABILITY_RESPONSE] content-type={ct}")

        except Exception as e:
            last_err = e
            time.sleep(0.7 * (attempt + 1))

    raise RuntimeError(f"Stability generate failed: {last_err}")

def put_png_to_s3(bucket: str, key: str, png_bytes: bytes):
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=png_bytes,
        ContentType="image/png",
        CacheControl="no-cache",
    )

def stable_seed_from_id(article_id: int) -> int:
    h = hashlib.sha256(str(article_id).encode("utf-8")).hexdigest()
    return int(h[:8], 16)

def lambda_handler(event, context):
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

        prompt_en = openai_make_prompt(title, summary)
        seed = stable_seed_from_id(int(article_id))
        png = generate_image_stability(prompt_en, seed)

        key = f"{out_prefix}/{date_str}/{article_id}.png"
        put_png_to_s3(bucket, key, png)
        results.append({"id": article_id, "s3_key": key})

    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True, "date": date_str, "count": len(results), "saved": results}, ensure_ascii=False)
    }
