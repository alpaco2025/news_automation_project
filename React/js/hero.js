// hero.js
document.addEventListener("DOMContentLoaded", () => {
  const hero = document.querySelector(".hero");

  if (!hero) return;

  // 약간의 딜레이 후 애니메이션 시작
  setTimeout(() => {
    hero.classList.add("show");
  }, 300);
});
