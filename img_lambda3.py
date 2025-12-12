# %%
# 뉴스 요약 기반 자동 이미지 생성 (Stable Diffusion + OpenAI 번역)


import os
import requests
import base64

from openai import OpenAI


# ==========================================================
# 1) API Keys
OPENAI_API_KEY = 
STABILITY_API_KEY = 


client = OpenAI(api_key=OPENAI_API_KEY)

STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"


# ==========================================================
# 2) 한국어 summary → 영어 번역
# ==========================================================
def translate_to_english(text_kr: str) -> str:
    """
    OpenAI로 한국어 summary를 자연스러운 영어 뉴스 문장으로 변환
    """
    prompt = f"""
    Translate the following Korean news text into clear, concise, professional English.

    Korean:
    {text_kr}

    English:
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        raise RuntimeError(f"[TRANSLATION_ERROR] {e}")


# ==========================================================
# 3) 제목 번역 (짧고 명확한 영어 헤드라인)
# ==========================================================
def translate_title(title_kr: str) -> str:
    prompt = f"""
    Translate the following Korean news headline into a short, impactful English headline:
    {title_kr}
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        raise RuntimeError(f"[TITLE_TRANSLATION_ERROR] {e}")


# ==========================================================
# 4) 이미지 생성 프롬프트 구성
# ==========================================================
def build_prompt_en(title_en: str, summary_en: str) -> str:
    """
    Stability AI에서 얼굴이 깨지지 않고 뉴스 스타일 이미지를 만들도록 프롬프트 최적화
    """
    return (
        "Create a highly detailed, realistic, cinematic-style news thumbnail image. "
        f"Headline topic: {title_en}. "
        f"Key points: {summary_en}. "
        "Focus on modern lighting, clean composition, and symbolic visual storytelling. "
        "If people appear, ensure perfectly natural eyes, symmetrical face structure, "
        "no distortions, no extra limbs, no warped hands, no artifacts. "
        "Style: photorealistic, ultra-detailed, professional news image. "
        "Do NOT include any text or captions in the image."
    )


# ==========================================================
# 5) Stability 이미지 생성
# ==========================================================
def generate_image_stability(prompt_en: str) -> bytes:
    """
    Stability API로 이미지 생성 후 PNG bytes 반환
    """
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {STABILITY_API_KEY}"
    }

    payload = {
        "prompt": prompt_en,
        "output_format": "png",
        "cfg_scale": 7,
        "steps": 40,
        "aspect_ratio": "16:9",
        "style_preset": "photographic",
        "seed": 123456,  # 결과 일관성 ↑
    }

    response = requests.post(
        STABILITY_URL,
        headers=headers,
        files={"none": ""},  # Stability 형식상 필요
        data=payload
    )

    if response.status_code != 200:
        raise RuntimeError(f"[IMAGE_GENERATION_ERROR] {response.text}")

    data = response.json()

    if "image" not in data:
        raise RuntimeError(f"[INVALID_RESPONSE] {data}")

    return base64.b64decode(data["image"])


# ==========================================================
# 6) Lambda3 메인 함수 (DB가 호출할 유일한 함수)
# ==========================================================
def generate_news_image(title_kr: str, summary_kr: str) -> bytes:
    """
    입력: 한국어 제목 + 요약
    출력: PNG 이미지 bytes (파일명은 DB가 생성)
    """

    # 1) 번역
    title_en = translate_title(title_kr)
    summary_en = translate_to_english(summary_kr)

    # 2) 이미지 프롬프트 생성
    prompt_en = build_prompt_en(title_en, summary_en)

    # 3) Stability 이미지 생성
    return generate_image_stability(prompt_en)


# ==========================================================
# 7) 로컬 개발자 테스트 코드 (DB에게 전달하지 않아도 됨)
# ==========================================================
if __name__ == "__main__":
    title = "머스크·베이조스, 우주 데이터센터 구축 경쟁 벌여"
    summary = (
        "- 일론 머스크와 제프 베이조스가 우주 데이터센터 구축 경쟁에 나섰다. "
        "- 블루오리진과 스페이스X는 AI 데이터센터 기술을 발전시키고 있다. "
        "- 우주 데이터센터는 냉각 비용이 낮고 효율적이다. "
        "- 글로벌 테크 기업들이 시장 경쟁을 확대하고 있다."
    )

    print("=== 이미지 생성 테스트 시작 ===")
    img = generate_news_image(title, summary)

    with open("test_news_image.png", "wb") as f:
        f.write(img)

    print("완료 → test_news_image.png 저장됨")



