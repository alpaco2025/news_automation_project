console.log("🌍 environment detect");

const host = location.hostname;

let API_BASE = "";

// 1️⃣ 로컬 개발
if (host === "localhost" || host === "127.0.0.1") {
  API_BASE = "http://127.0.0.1:8000";
}

// 2️⃣ GitHub Pages (운영)
else if (host.includes("github.io")) {
  API_BASE = "https://ainewsapi.duckdns.org";
}

// 3️⃣ EC2 내부 / 기타 (옵션)
else {
  API_BASE = "http://127.0.0.1:8000";
}

console.log("✅ API_BASE =", API_BASE);

// 전역 노출
window.API_BASE = API_BASE;
