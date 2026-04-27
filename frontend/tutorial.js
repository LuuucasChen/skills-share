/* =========================================================
   Skill Share — 使用教程页面交互逻辑
   ========================================================= */

const API_BASE = "";

// =========================================================
// 文档卡片折叠 + Markdown 懒加载
// =========================================================
const docCards = document.querySelectorAll(".doc-card");

docCards.forEach((card) => {
    const header = card.querySelector(".doc-card-header");
    const body   = card.querySelector(".doc-card-body");
    const mdLoad = card.querySelector(".md-loading");
    const mdContent = card.querySelector(".md-content");
    const filename = card.dataset.file;

    let loaded = false;

    header.addEventListener("click", async () => {
        const isOpen = card.classList.contains("open");
        card.classList.toggle("open", !isOpen);

        if (!isOpen && !loaded) {
            // 首次展开时懒加载 Markdown
            loaded = true;
            try {
                const res = await fetch(`${API_BASE}/api/markdown/${filename}`);
                if (!res.ok) {
                    const err = await res.json().catch(() => ({ detail: `请求失败 (${res.status})` }));
                    throw new Error(err.detail || `请求失败 (${res.status})`);
                }
                const text = await res.text();

                // 使用 marked.js 渲染 Markdown
                if (typeof marked !== "undefined") {
                    mdContent.innerHTML = marked.parse(text);
                } else {
                    // 降级：纯文本显示
                    const pre = document.createElement("pre");
                    pre.textContent = text;
                    mdContent.appendChild(pre);
                }

                mdLoad.style.display = "none";
                mdContent.style.display = "";
            } catch (err) {
                mdLoad.textContent = `加载失败：${err.message}`;
            }
        }
    });
});

// =========================================================
// 平滑滚动导航（URL hash 跳转）
// =========================================================
document.querySelectorAll("a[href^='#']").forEach((a) => {
    a.addEventListener("click", (e) => {
        const target = document.querySelector(a.getAttribute("href"));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    });
});
