console.log("news.js loaded (today + previous + search + Polly TTS)");

const todayGrid = document.getElementById("newsGrid");
const pastGrid  = document.getElementById("pastNewsGrid");

const newsModal = document.getElementById("newsModal");
const modalClose = document.getElementById("newsModalClose");
const modalTitle = document.getElementById("modalTitle");
const modalSummary = document.getElementById("modalSummary");
const modalKeywords = document.getElementById("modalKeywords");

/* ================================
   🔧 설정값
================================ */
const TODAY_NEWS_LIMIT = 200;
const PREVIOUS_NEWS_LIMIT = 200;

/* ================================
   🔊 Polly TTS (최소)
================================ */
const S3_BASE = "https://news-automation-public.s3.ap-northeast-2.amazonaws.com";
const IMAGE_PREFIX = "news/images";
const TTS_PREFIX = "news/tts";

let _ttsAudio = null;

function getTtsUrl(date, articleId) {
  return `${S3_BASE}/${TTS_PREFIX}/${date}/${articleId}.mp3`;
}

function getImageUrl(date, articleId) {
  return `${S3_BASE}/${IMAGE_PREFIX}/${date}/${articleId}.png`;
}

function ttsStop() {
  if (_ttsAudio) {
    _ttsAudio.pause();
    _ttsAudio.currentTime = 0;
  }
}

function ttsPlay(url) {
  ttsStop();
  _ttsAudio = new Audio(url);
  _ttsAudio.play().catch(() => {
    alert("음성 파일이 없습니다.");
  });
}

/* ================================
   날짜 유틸
================================ */
function getDateFolder(article, fallbackDate) {
  // ✅ 1순위: Lambda created_at 기반으로 내려준 asset_date
  const ad2 = (article.asset_date || "").trim();
  if (ad2.length >= 10) return ad2.slice(0, 10);

  // 2순위: article_date
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

function addDays(dateStr, days) {
  // dateStr: "YYYY-MM-DD"
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

/* ================================
   ✅ 이미지/tts 날짜 보정 로더
   - 1) date 폴더로 시도
   - 2) 실패하면 date+1 폴더로 재시도
================================ */
function loadWithDateFallback(imgEl, baseDate, articleId) {
  if (!imgEl || !baseDate) return;

  const try1 = getImageUrl(baseDate, articleId);
  const try2 = getImageUrl(addDays(baseDate, 1), articleId);

  imgEl.src = try1;
  imgEl.onerror = () => {
    imgEl.onerror = () => {
      // 둘 다 실패 → 이미지 영역 숨김
      if (imgEl.parentElement) imgEl.parentElement.style.display = "none";
    };
    imgEl.src = try2;
  };
}

function getTtsUrlWithFallback(baseDate, articleId) {
  // TTS도 동일하게 date / date+1 둘 다 가능성 대비
  const d1 = baseDate;
  const d2 = addDays(baseDate, 1);
  return {
    primary: getTtsUrl(d1, articleId),
    secondary: getTtsUrl(d2, articleId),
  };
}

/* ================================
   뉴스 카드 생성 (S3 뉴스)
================================ */
function createNewsCard(article, fallbackDate) {
  const card = document.createElement("article");
  card.className = "card";

  const date = article.asset_date || getDateFolder(article, fallbackDate);

  card.innerHTML = `
    <div class="news-card-image-wrap">
      <img class="news-thumb" alt="" />
      <div class="news-card-ai-label">AI로 생성된 이미지</div>
    </div>

    <div class="news-date">${date}</div>
    <div class="news-title">${article.title}</div>

    <div class="news-keywords">
      ${(article.keywords || []).map(k => `<span>#${k}</span>`).join("")}
    </div>
  `;

  // ✅ 이미지 로드(날짜 폴더 보정)
  const imgEl = card.querySelector(".news-thumb");
  loadWithDateFallback(imgEl, date, article.id);

  card.addEventListener("click", () => {
    openNewsModal(article, date);
  });

  return card;
}

/* ================================
   🔍 검색 결과 카드 생성 (FastAPI)
   - S3 카드랑 같은 UI로 맞춤 (이미지/날짜/키워드)
================================ */
function createSearchResultCard(article, fallbackDate = "") {
  const card = document.createElement("article");
  card.className = "card";

  const date = article.asset_date || getDateFolder(article, fallbackDate);

  // keywords가 배열/문자열 모두 대응
  let keywordsArr = [];
  if (Array.isArray(article.keywords)) {
    keywordsArr = article.keywords;
  } else if (typeof article.keywords === "string") {
    keywordsArr = article.keywords.split(",").map(k => k.trim()).filter(Boolean);
  }

  card.innerHTML = `
    <div class="news-card-image-wrap">
      <img class="news-thumb" alt="" />
      <div class="news-card-ai-label">AI로 생성된 이미지</div>
    </div>

    <div class="news-date">${date}</div>
    <div class="news-title">${article.title}</div>

    <div class="news-keywords">
      ${keywordsArr.map(k => `<span>#${k}</span>`).join("")}
    </div>
  `;

  const imgEl = card.querySelector(".news-thumb");
  loadWithDateFallback(imgEl, date, article.id);

  card.addEventListener("click", () => {
    const normalized = {
      ...article,
      keywords: keywordsArr,
      summary: article.summary || "",
    };
    openNewsModal(normalized, date);
  });

  return card;
}

/* ================================
   뉴스 모달 열기 (✅ 이미지 상단 TTS)
   - TTS도 date / date+1 자동 보정 시도
================================ */
function openNewsModal(article, date) {
  const { primary: tts1, secondary: tts2 } = getTtsUrlWithFallback(date, article.id);

  document.querySelectorAll(".news-modal-image-wrap").forEach(el => el.remove());

  modalTitle.insertAdjacentHTML(
    "beforebegin",
    `
    <div class="news-modal-image-wrap">
      <img class="news-modal-thumb" alt="" />

      <!-- 🔊 이미지 상단 TTS -->
      <div class="news-modal-tts">
        <button class="news-modal-tts-play" data-tts1="${tts1}" data-tts2="${tts2}">🔊 요약</button>
        <button class="news-modal-tts-stop">⏹ 정지</button>
      </div>

      <div class="news-modal-gradient"></div>

      <div class="news-modal-text">
        <div class="news-modal-title">${article.title}</div>
        <div class="news-modal-date">${date}</div>
      </div>

      <div class="news-modal-ai-label">AI로 생성된 이미지</div>
      <button class="news-modal-img-close">✕</button>
    </div>
    `
  );

  // ✅ 이미지 로드(날짜 폴더 보정)
  const imgEl = document.querySelector(".news-modal-thumb");
  loadWithDateFallback(imgEl, date, article.id);

  modalTitle.textContent = "";
  modalSummary.textContent = article.summary || "";

  modalKeywords.innerHTML = `
    <div class="news-keywords modal-keywords">
      ${(article.keywords || []).map(k => `<span>#${k}</span>`).join("")}
    </div>
  `;

  const playBtn = document.querySelector(".news-modal-tts-play");
  const stopBtn = document.querySelector(".news-modal-tts-stop");

  playBtn?.addEventListener("click", () => {
    const u1 = playBtn.dataset.tts1;
    const u2 = playBtn.dataset.tts2;

    // 1) date 폴더 mp3 먼저 시도
    ttsStop();
    _ttsAudio = new Audio(u1);
    _ttsAudio.onerror = () => {
      // 2) 실패하면 date+1 폴더 시도
      _ttsAudio = new Audio(u2);
      _ttsAudio.play().catch(() => alert("음성 파일이 없습니다."));
    };
    _ttsAudio.play().catch(() => {
      // play 실패(정책/자동재생 등) 처리
      alert("음성 재생이 차단됐습니다. 버튼을 다시 눌러주세요.");
    });
  });

  stopBtn?.addEventListener("click", () => ttsStop());

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
   뉴스 로딩 (S3)
================================ */
fetch(`${S3_BASE}/news/daily/latest.json?t=${Date.now()}`)
  .then(res => res.json())
  .then(data => {
    const articles = data.articles || [];
    const fallbackDate = data.date || "";

    const today = getToday();
    const yesterday = getYesterday();

    todayGrid.innerHTML = "";
    pastGrid.innerHTML = "";

    // 최신순 정렬
    articles.sort((a, b) => {
      const ta = new Date(a.article_date || a.date);
      const tb = new Date(b.article_date || b.date);
      return tb - ta;
    });

    let todayCount = 0;
    let pastCount = 0;

    for (const article of articles) {
      const d = getDateFolder(article, fallbackDate);
      if ((d === today || d === yesterday) && todayCount < TODAY_NEWS_LIMIT) {
        todayGrid.appendChild(createNewsCard(article, fallbackDate));
        todayCount += 1;
      } else if (pastCount < PREVIOUS_NEWS_LIMIT) {
        pastGrid.appendChild(createNewsCard(article, fallbackDate));
        pastCount += 1;
      }
      if (todayCount >= TODAY_NEWS_LIMIT && pastCount >= PREVIOUS_NEWS_LIMIT) break;
    }
  });

/* ================================
   검색 (FastAPI)
================================ */
async function searchNews(keyword) {
  const API_BASE = "https://ainewsapi.duckdns.org";

  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(keyword)}`);
  const data = await res.json();

  todayGrid.innerHTML = "";
  pastGrid.innerHTML = "";

  // 검색 결과 최신순 정렬 (article_date / created_at 기준)
  data.sort((a, b) => {
    const ta = new Date(a.article_date || a.created_at || a.date);
    const tb = new Date(b.article_date || b.created_at || b.date);
    return tb - ta;
  });

  data.forEach(article => {
    todayGrid.appendChild(createSearchResultCard(article));
  });
}

