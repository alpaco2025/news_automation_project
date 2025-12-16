console.log("header-search.js loaded");

// 🔴 전역 키 이벤트 확인
document.addEventListener("keydown", e => {
  console.log("DOCUMENT keydown:", e.key);
});

// 🔴 전역 클릭 이벤트 확인
document.addEventListener("click", e => {
  console.log("DOCUMENT click:", e.target);
});

// 🔴 input 요소 확인
const mainSearchInput = document.getElementById("mainSearchInput");
const mainSearchBtn = document.getElementById("mainSearchBtn");

console.log("input element:", mainSearchInput);
console.log("button element:", mainSearchBtn);
