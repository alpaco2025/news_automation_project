import os
import time
import requests
from typing import Tuple

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.2
MAX_TOKENS = 700

SUMMARY_PROMPT = """
당신은 뉴스 요약 전문가입니다.

아래 기사 제목과 본문 내용을 읽고:

1) 기사 핵심 내용을 4문장으로 요약해 주세요.
2) 기사 핵심 키워드 5개를 bullet 형식으로 출력해 주세요.

출력 형식은 아래처럼 '텍스트'로만 출력하세요. JSON 금지.

예시 출력:
요약:
- 문장1
- 문장2
- 문장3
- 문장4

키워드:
- 키워드1
- 키워드2
- 키워드3
- 키워드4
- 키워드5

제목: {title}

본문:
{body}
"""


def _get_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 없습니다.")
    return api_key


def _call_openai_chat(prompt: str) -> str:
    """
    OpenAI Chat Completions HTTP API를 직접 호출하는 함수.
    """
    api_key = _get_api_key()

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    json_body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }

    resp = requests.post(url, headers=headers, json=json_body, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    return data["choices"][0]["message"]["content"]


def summarize_article(title: str, content: str) -> str:
    """
    기사 제목/본문을 받아 LLM 요약(raw text)을 반환.
    """
    if len(content) > 8000:
        content = content[:8000]

    prompt = SUMMARY_PROMPT.format(title=title, body=content)

    for attempt in range(3):
        try:
            raw = _call_openai_chat(prompt)
            return raw
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"요약 생성 실패: {e}")
            time.sleep(0.5)


def parse_summary_output(raw_text: str) -> Tuple[str, str]:
    """
    LLM에서 받은 raw text를 summary / keywords 문자열로 분리.
    """
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    summary_lines = []
    keyword_lines = []
    mode = None

    for line in lines:
        if line.startswith("요약"):
            mode = "summary"
            continue
        elif line.startswith("키워드"):
            mode = "keywords"
            continue

        if mode == "summary" and line.startswith("-"):
            summary_lines.append(line.lstrip("- ").strip())
        elif mode == "keywords" and line.startswith("-"):
            keyword_lines.append(line.lstrip("- ").strip())

    summary_str = " ".join(summary_lines)
    keywords_str = ", ".join(keyword_lines)

    return summary_str, keywords_str
