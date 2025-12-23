console.log("search.js loaded");

const params = new URLSearchParams(window.location.search);
const keyword = params.get("q");

const grid = document.getElementById("searchResultGrid");
if (!grid) {
  console.warn("searchResultGrid not found");
} else if (!keyword || !keyword.trim()) {
  grid.innerHTML = "<p>검색어가 없습니다.</p>";
} else {
  searchNews(keyword.trim());
}

async function searchNews(keyword) {
  const API_BASE = "https://ainewsapi.duckdns.org";

  try {
    const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(keyword)}`);
    if (!res.ok) throw new Error(`검색 API 오류: ${res.status}`);

    const data = await res.json();
    const articles = Array.isArray(data?.results) ? data.results : [];

    if (articles.length === 0) {
      grid.innerHTML = "<p>검색 결과가 없습니다.</p>";
      return;
    }

    grid.innerHTML = "";

    const canUseCard = typeof window.createNewsCard === "function";

    articles.forEach((article) => {
      // ✅ FastAPI 결과를 news 카드에 맞게 정규화
      const normalized = {
        id: article.id || article.article_id || `search-${Math.random()}`,
        title: article.title || "",
        summary: article.summary || "",
        article_date: article.article_date || article.date || article.published_at || "",
        asset_date: article.asset_date || "",
        keywords: Array.isArray(article.keywords)
          ? article.keywords
          : typeof article.keywords === "string"
            ? article.keywords.split(",").map(k => k.trim()).filter(Boolean)
            : [],
      };

      const dateForCard = normalized.asset_date || normalized.article_date || "";

      if (canUseCard) {
        const card = window.createNewsCard(normalized, dateForCard);
        grid.appendChild(card);
      } else {
        // fallback
        const div = document.createElement("div");
        div.className = "card";
        div.innerHTML = `
          <h3>${escapeHtml(normalized.title)}</h3>
          <p>${escapeHtml(normalized.summary)}</p>
          <small>${escapeHtml(dateForCard)}</small>
        `;
        grid.appendChild(div);
      }
    });
  } catch (err) {
    console.error("검색 실패:", err);
    grid.innerHTML = "<p>검색 중 오류가 발생했습니다.</p>";
  }
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

