/* ================================
   Header Search – Step 4 (JS)
   검색 전용 파일
================================ */

console.log("header-search.js loaded");


// 검색 요소
const mainSearchInput = document.getElementById("mainSearchInput");
const mainSearchBtn   = document.getElementById("mainSearchBtn");

// 검색 실행 함수 (공통)
function runMainSearch() {
  if (!mainSearchInput) return;

  const q = mainSearchInput.value.trim();
  if (!q) return;

  window.location.href =
    `search.html?q=${encodeURIComponent(mainSearchInput.value)}`;

}

// Enter 키
if (mainSearchInput) {
  mainSearchInput.addEventListener("keydown", e => {
    if (e.key === "Enter") {
      runMainSearch();
    }
  });
}

// 버튼 클릭
if (mainSearchBtn) {
  mainSearchBtn.addEventListener("click", runMainSearch);
}
