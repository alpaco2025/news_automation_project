console.log("header-search.js loaded");

document.addEventListener("DOMContentLoaded", () => {

  const inputEl =
    document.getElementById("mainSearchInput") ||
    document.getElementById("searchInput");

  const btnEl =
    document.getElementById("mainSearchBtn") ||
    document.getElementById("searchBtn");

  if (!inputEl || !btnEl) {
    console.warn("❌ 검색 input/button 요소를 찾지 못했습니다.");
    return;
  }

  // Enter → 버튼 클릭
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      btnEl.click();
    }
  });

  // 검색 버튼 클릭 → search.html 이동
  btnEl.addEventListener("click", () => {
    const keyword = (inputEl.value || "").trim();
    if (!keyword) return;

    // ✅ 같은 폴더 → 상대경로
    window.location.href =
      `search.html?q=${encodeURIComponent(keyword)}`;
  });

});
