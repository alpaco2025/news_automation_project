console.log("news.js loaded (today + previous FINAL + Polly TTS)");

const todayGrid = document.getElementById("newsGrid");      // Today News
const pastGrid  = document.getElementById("pastNewsGrid"); // Previous News

const newsModal = document.getElementById("newsModal");
const modalClose = document.getElementById("newsModalClose");
const modalTitle = document.getElementById("modalTitle");
const modalSummary = document.getElementById("modalSummary");
const modalKeywords = document.getElementById("modalKeywords");

/* ================================
   🔧 설정값
================================ */
const TODAY_NEWS_LIMIT = 30;
const PREVIOUS_NEWS_LIMIT = 30;

/* ================================
   🔊 Polly TTS 설정 (S3 mp3)
================================ */
const S3_BASE = "https://news-automation-public.s3.ap-northeast-2.amazonaws.com";
const TTS_PREFIX = "news/tts"; // Lambda5가 저장하는 prefix와 동일해야 함

let _ttsAudio = null;

function getTtsUrl(date, articleId) {
  // 예: https://.../news/tts/2025-12-16/245.mp3
  return `${S3_BASE}/${TTS_PREFIX}/${date}/${articleId}.mp3`;
}

function ttsStop() {
  if (_ttsAudio) {
    try {
      _ttsAudio.pause();
      _ttsAudio.currentTime = 0;
    } catch (e) {}
  }
}

function ttsPlay(url) {
  ttsStop();
  _ttsAudio = new Audio(url);
  _ttsAudio.preload = "none";
  _ttsAudio.play().catch(err => {
    console.warn("TTS 재생 실패:", err);
    alert("음성 재생에 실패했어요. (mp3가 없거나 권한/경로 문제일 수 있어요)");
  });
}

/* ================================
   날짜 유틸
================================ */
function getDateFolder(article, fallbackDate) {
  const ad = (article.article_date || "").trim();
  const fromArticleDate = ad.length >= 10 ? ad.slice(0, 10) : "";
  return fromArticleDate || article.date || fallbackDate || "";
}

function getToday() {
  return new Date().toISOString().slice(0, 10);
}

function getYesterday() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

/* ================================
   뉴스 카드 생성 (기존 뉴스)
================================ */
function createNewsCard(article, fallbackDate) {
  const card = document.createElement("article");
  card.className = "card";

  const date = getDateFolder(article, fallbackDate);

  const imageUrl =
    `${S3_BASE}/news/images/${date}/${article.id}.png`;

  const ttsUrl = getTtsUrl(date, article.id);

  card.innerHTML = `
    <div class="news-card-image-wrap">
      <img class="news-thumb"
           src="${imageUrl}"
           alt=""
           onerror="this.parentElement.style.display='none'" />
      <div class="news-card-ai-label">AI로 생성된 이미지</div>
    </div>

    <div class="news-date">${date}</div>
    <div class="news-title">${article.title}</div>

    <div class="news-keywords">
      ${(article.keywords || []).map(k => `<span>#${k}</span>`).join("")}
    </div>

    <!-- 🔊 TTS 버튼 -->
    <div class="news-tts-wrap" style="margin-top:10px; display:flex; gap:8px;">
      <button type="button" class="news-tts-btn" data-tts="${ttsUrl}">🔊 요약 듣기</button>
      <button type="button" class="news-tts-stop-btn">⏹ 정지</button>
    </div>
  `;

  // 카드 클릭 시 모달 열기 (단, TTS 버튼 클릭은 제외)
  card.addEventListener("click", (e) => {
    if (
      e.target &&
      (e.target.classList.contains("news-tts-btn") ||
       e.target.classList.contains("news-tts-stop-btn"))
    ) return;

    openNewsModal(article, date);
  });

  // 카드 TTS 이벤트
  const playBtn = card.querySelector(".news-tts-btn");
  const stopBtn = card.querySelector(".news-tts-stop-btn");

  playBtn.addEventListener("click", async () => {
    const url = playBtn.getAttribute("data-tts");
    ttsPlay(url);
  });

  stopBtn.addEventListener("click", () => ttsStop());

  return card;
}

/* ================================
   🔍 검색 결과 카드 생성 (FastAPI)
   (검색 결과는 date 정보가 없을 수 있으니, TTS는 기본 비활성/숨김 처리)
================================ */
function createSearchResultCard(article) {
  const card = document.createElement("article");
  card.className = "card";

  const keywords = article.keywords
    ? article.keywords.split(",").map(k => k.trim())
    : [];

  card.innerHTML = `
    <div class="news-title">${article.title}</div>

    <p style="font-size:15px; line-height:1.6; color:#333;">
      ${article.summary}
    </p>

    <div class="news-keywords">
      ${keywords.map(k => `<span>#${k}</span>`).join("")}
    </div>
  `;

  card.addEventListener("click", () => {
    window.open(article.url, "_blank");
  });

  return card;
}

/* ================================
   뉴스 모달 열기 (+ Polly TTS 버튼)
================================ */
function openNewsModal(article, date) {
  const imageUrl =
    `${S3_BASE}/news/images/${date}/${article.id}.png`;

  const ttsUrl = getTtsUrl(date, article.id);

  document
    .querySelectorAll(".news-modal-image-wrap")
    .forEach(el => el.remove());

  modalTitle.insertAdjacentHTML(
    "beforebegin",
    `
    <div class="news-modal-image-wrap">
      <img class="news-modal-thumb"
           src="${imageUrl}"
           alt=""
           onerror="this.parentElement.style.display='none'" />

      <div class="news-modal-gradient"></div>

      <div class="news-modal-text">
        <div class="news-modal-title">${article.title}</div>
        <div class="news-modal-date">${date}</div>
      </div>

      <div class="news-modal-ai-label">AI로 생성된 이미지</div>

      <!-- 🔊 모달 TTS 버튼 -->
      <div class="news-modal-tts" style="position:absolute; left:16px; bottom:16px; display:flex; gap:8px; z-index:5;">
        <button type="button" class="news-modal-tts-play" data-tts="${ttsUrl}">🔊 요약 듣기</button>
        <button type="button" class="news-modal-tts-stop">⏹ 정지</button>
      </div>

      <button class="news-modal-img-close" aria-label="모달 닫기">✕</button>
    </div>
    `
  );

  modalTitle.textContent = "";
  modalSummary.textContent = article.summary;

  modalKeywords.innerHTML = `
    <div class="news-keywords modal-keywords">
      ${(article.keywords || []).map(k => `<span>#${k}</span>`).join("")}
    </div>
  `;

  // 모달 TTS 이벤트 바인딩
  const playBtn = document.querySelector(".news-modal-tts-play");
  const stopBtn = document.querySelector(".news-modal-tts-stop");

  if (playBtn) {
    playBtn.addEventListener("click", () => {
      const url = playBtn.getAttribute("data-tts");
      ttsPlay(url);
    });
  }
  if (stopBtn) {
    stopBtn.addEventListener("click", () => ttsStop());
  }

  newsModal.classList.add("active");
}

/* ================================
   모달 닫기
================================ */
document.addEventListener("click", e => {
  if (
    e.target.classList.contains("news-modal-img-close") ||
    e.target.classList.contains("news-modal-overlay")
  ) {
    ttsStop();
    newsModal.classList.remove("active");
  }
});

modalClose.addEventListener("click", () => {
  ttsStop();
  newsModal.classList.remove("active");
});

/* ================================
   🔥 뉴스 로딩 (S3)
================================ */
const LATEST_URL =
  `${S3_BASE}/news/daily/latest.json`;

fetch(LATEST_URL)
  .then(res => {
    if (!res.ok) throw new Error("latest.json 응답 오류");
    return res.json();
  })
  .then(data => {
    const articles = data.articles || [];
    const fallbackDate = data.date || "";

    const today = getToday();
    const yesterday = getYesterday();

    if (articles.length === 0) {
      todayGrid.innerHTML = "<p>오늘 뉴스가 없습니다.</p>";
      pastGrid.innerHTML = "<p>이전 뉴스가 없습니다.</p>";
      return;
    }

    articles.sort((a, b) => {
      const ta = new Date(a.article_date || a.date);
      const tb = new Date(b.article_date || b.date);
      return tb - ta;
    });

    todayGrid.innerHTML = "";
    pastGrid.innerHTML = "";

    const todayArticles = [];
    const pastArticles = [];

    articles.forEach(article => {
      const d = getDateFolder(article, fallbackDate);
      if (d === today || d === yesterday) {
        todayArticles.push(article);
      } else {
        pastArticles.push(article);
      }
    });

    todayArticles
      .slice(0, TODAY_NEWS_LIMIT)
      .forEach(a => todayGrid.appendChild(createNewsCard(a, fallbackDate)));

    pastArticles
      .slice(0, PREVIOUS_NEWS_LIMIT)
      .forEach(a => pastGrid.appendChild(createNewsCard(a, fallbackDate)));
  })
  .catch(err => {
    console.error("뉴스 로딩 실패:", err);
    todayGrid.innerHTML = "<p>뉴스를 불러오지 못했습니다.</p>";
    pastGrid.innerHTML = "<p>뉴스를 불러오지 못했습니다.</p>";
  });

/* ================================
   🔍 검색 (FastAPI)
================================ */
async function searchNews(keyword) {
  const API_BASE = "https://ainewsapi.duckdns.org";

  try {
    const res = await fetch(
      `${API_BASE}/search?q=${encodeURIComponent(keyword)}`
    );

    if (!res.ok) throw new Error("검색 API 오류");

    const data = await res.json();

    todayGrid.innerHTML = "";
    pastGrid.innerHTML = "";

    if (data.length === 0) {
      todayGrid.innerHTML = "<p>검색 결과가 없습니다.</p>";
      return;
    }

    data.forEach(article => {
      todayGrid.appendChild(createSearchResultCard(article));
    });

  } catch (err) {
    console.error("검색 실패:", err);
    todayGrid.innerHTML = "<p>검색 중 오류가 발생했습니다.</p>";
  }
}

/* ================================
   🔍 검색 입력 이벤트
================================ */
document.addEventListener("DOMContentLoaded", () => {
  const mainSearchInput = document.getElementById("mainSearchInput");
  const mainSearchBtn   = document.getElementById("mainSearchBtn");

  if (!mainSearchInput || !mainSearchBtn) {
    console.warn("검색 요소 없음");
    return;
  }

  // Enter 키
  mainSearchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      mainSearchBtn.click();
    }
  });

  // 버튼 클릭
  mainSearchBtn.addEventListener("click", () => {
    const keyword = mainSearchInput.value.trim();
    console.log("🔍 검색:", keyword);
    if (!keyword) return;

    searchNews(keyword);
  });
});
