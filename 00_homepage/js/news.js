console.log("news.js loaded (today + previous FINAL)");

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
   뉴스 카드 생성
================================ */
function createNewsCard(article, fallbackDate) {
  const card = document.createElement("article");
  card.className = "card";

  const date = getDateFolder(article, fallbackDate);
  const imageUrl =
    `https://news-automation-public.s3.ap-northeast-2.amazonaws.com/news/images/${date}/${article.id}.png`;

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
  `;

  card.addEventListener("click", () => {
    openNewsModal(article, date);
  });

  return card;
}

/* ================================
   뉴스 모달 열기 (날짜 위치 FIX)
================================ */
function openNewsModal(article, date) {
  const imageUrl =
    `https://news-automation-public.s3.ap-northeast-2.amazonaws.com/news/images/${date}/${article.id}.png`;

  /* 🔥 기존 이미지 / 날짜 제거 (중복 방지) */
  document.querySelectorAll(".news-modal-image-wrap, .modal-date-under-image")
    .forEach(el => el.remove());

  /* 1️⃣ 이미지 삽입 */
  modalTitle.insertAdjacentHTML(
    "beforebegin",
    `
    <div class="news-modal-image-wrap">
      <img class="news-modal-thumb"
           src="${imageUrl}"
           alt=""
           onerror="this.parentElement.style.display='none'" />
      <div class="news-modal-ai-label">AI로 생성된 이미지</div>
    </div>
    `
  );

  /* 2️⃣ 날짜를 이미지 바로 아래에 삽입 */
  const imageEl = document.querySelector(".news-modal-image-wrap");
  imageEl.insertAdjacentHTML(
    "afterend",
    `<div class="modal-date-under-image">${date}</div>`
  );

  /* 3️⃣ 제목 / 본문 */
  modalTitle.textContent = article.title;
  modalSummary.textContent = article.summary;

  /* 4️⃣ 키워드만 */
  modalKeywords.innerHTML = `
    <div class="news-keywords modal-keywords">
      ${(article.keywords || []).map(k => `<span>#${k}</span>`).join("")}
    </div>
  `;

  newsModal.classList.add("active");
}

/* ================================
   모달 닫기
================================ */
modalClose.addEventListener("click", () => {
  newsModal.classList.remove("active");
});

newsModal.addEventListener("click", e => {
  if (e.target.classList.contains("news-modal-overlay")) {
    newsModal.classList.remove("active");
  }
});

/* ================================
   🔥 뉴스 로딩 (유지)
================================ */
const LATEST_URL =
  "https://news-automation-public.s3.ap-northeast-2.amazonaws.com/news/daily/latest.json";

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

    /* 최신순 정렬 */
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
