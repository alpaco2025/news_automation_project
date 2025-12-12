# %%
# ==========================================================
# Lambda3: 뉴스 요약 기반 자동 이미지 생성
# Provider: Stability AI
# Model: stable-image/generate/core
# ==========================================================

import os
import requests
import base64
from openai import OpenAI


# ==========================================================
# 1) API Keys (환경변수 사용 권장)
# ==========================================================
OPENAI_API_KEY = 
STABILITY_API_KEY = 
client = OpenAI(api_key=OPENAI_API_KEY)

STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"


# ==========================================================
# 2) 한국어 summary → 영어 번역
# ==========================================================
def translate_to_english(text_kr: str) -> str:
    prompt = f"""
    Translate the following Korean news summary into clear,
    concise, professional English suitable for a news article.

    Korean:
    {text_kr}

    English:
    """

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=300
    )

    return resp.choices[0].message.content.strip()


# ==========================================================
# 3) 제목 번역 (뉴스 헤드라인용)
# ==========================================================
def translate_title(title_kr: str) -> str:
    prompt = f"""
    Translate the following Korean news headline into a short,
    impactful English headline:

    {title_kr}
    """

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=100
    )

    return resp.choices[0].message.content.strip()


# ==========================================================
# 4) 이미지 생성 프롬프트
# ==========================================================
def build_prompt_en(title_en: str, summary_en: str) -> str:
    """
    Stability 기준 최적화된 뉴스 썸네일 프롬프트
    """
    return (
        "Create a highly detailed, realistic, cinematic-style news thumbnail image. "
        f"Headline topic: {title_en}. "
        f"Key context: {summary_en}. "
        "Focus on modern lighting, clean composition, and symbolic visual storytelling. "
        "If people appear, ensure natural eyes, symmetrical face structure, "
        "no distortions, no extra limbs, no warped hands, no artifacts. "
        "Style: photorealistic, professional news image. "
        "Do NOT include any text or captions in the image."
    )


# ==========================================================
# 5) Stability 이미지 생성 (비용 절감 세팅)
# ==========================================================
def generate_image_stability(prompt_en: str) -> bytes:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {STABILITY_API_KEY}"
    }

    payload = {
        "prompt": prompt_en,
        "output_format": "png",
        "cfg_scale": 6.0,          # 기존 7 → 6.5
        "steps": 28,               # 기존 40 → 32 (약 15~20% 절감)
        "aspect_ratio": "16:9",
        "style_preset": "photographic",
        "seed": 123456             # 결과 일관성
    }

    response = requests.post(
        STABILITY_URL,
        headers=headers,
        files={"none": ""},
        data=payload,
        timeout=90
    )

    if response.status_code != 200:
        raise RuntimeError(f"[STABILITY_IMAGE_ERROR] {response.text}")

    data = response.json()

    if "image" not in data:
        raise RuntimeError(f"[INVALID_STABILITY_RESPONSE] {data}")

    return base64.b64decode(data["image"])


# ==========================================================
# 6) Lambda3 메인 함수 (DB / Lambda2가 호출)
# ==========================================================
def generate_news_image(title_kr: str, summary_kr: str) -> bytes:
    """
    입력:
        title_kr   : 한국어 기사 제목
        summary_kr : 한국어 기사 요약 (Lambda2 결과)

    출력:
        PNG 이미지 bytes
    """

    title_en = translate_title(title_kr)
    summary_en = translate_to_english(summary_kr)

    prompt_en = build_prompt_en(title_en, summary_en)

    return generate_image_stability(prompt_en)


# ==========================================================
# 7) 로컬 테스트
# ==========================================================
if __name__ == "__main__":

    title = "딥시크, 차세대 모델 개발에 '블랙웰' 칩 사용...내년 2월 출시 목표"
    summary = (
        "중국 딥시크가 엔비디아의 차세대 '블랙웰' 칩을 밀반입해 차세대 모델 개발에 활용하고 있으며, 내년 2월 출시를 목표로 하고 있다. "
        "블랙웰 칩은 '희소 어텐션' 기법에 최적화되어 있어, 차세대 모델 개발에 필수적이다. "
        "딥시크는 기존 모델의 업그레이드에 그쳤으나, 블랙웰 칩 확보로 새로운 모델 출시를 앞두고 있다."
        "엔비디아는 밀반입 사실에 대한 구체적 증거는 없다고 밝혔지만, 관련 제보에 대해서는 추적하겠다고 했다."
    )

    print("이미지 생성 중...")

    img = generate_news_image(title, summary)

    with open("final_news_thumbnail.png", "wb") as f:
        f.write(img)

    print("✅ final_news_thumbnail.png 생성 완료")



