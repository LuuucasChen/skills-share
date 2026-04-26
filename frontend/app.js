/* =========================================================
   技能共享平台 — 前端交互逻辑
   ========================================================= */

const API_BASE = "";

// ========== DOM 引用 ==========
const skillsGrid = document.getElementById("skillsGrid");
const searchInput = document.getElementById("searchInput");
const searchClear = document.getElementById("searchClear");
const skeletonGrid = document.getElementById("skeletonGrid");
const loading = document.getElementById("loading");
const emptyState = document.getElementById("empty");
const errorState = document.getElementById("error");
const errorMessage = document.getElementById("errorMessage");
const uploadBtn = document.getElementById("uploadBtn");
const modalOverlay = document.getElementById("modalOverlay");
const modalClose = document.getElementById("modalClose");
const cancelBtn = document.getElementById("cancelBtn");
const uploadForm = document.getElementById("uploadForm");
const uploadProgress = document.getElementById("uploadProgress");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const submitBtn = document.getElementById("submitBtn");
const toastContainer = document.getElementById("toastContainer");
const fileList = document.getElementById("fileList");
const fileInput = document.getElementById("skillFile");
const fileZone = document.getElementById("fileZone");

const totalSkillsEl = document.getElementById("totalSkills");
const totalFilesEl = document.getElementById("totalFiles");
const totalTagsEl = document.getElementById("totalTags");
const descEl = document.getElementById("skillDesc");
const descCountEl = document.getElementById("descCount");

// 历史版本弹窗
const versionModalOverlay = document.getElementById("versionModalOverlay");
const versionModalClose = document.getElementById("versionModalClose");
const versionModalTitle = document.getElementById("versionModalTitle");
const versionModalSubtitle = document.getElementById("versionModalSubtitle");
const versionLoading = document.getElementById("versionLoading");
const versionList = document.getElementById("versionList");

let allSkills = [];

// =========================================================
// Toast
// =========================================================
function showToast(message, type = "success", duration = 3500) {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    const iconSvg = type === "success"
        ? `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`
        : `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

    toast.innerHTML = iconSvg + `<span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "toastOut 0.3s ease forwards";
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// =========================================================
// 格式化
// =========================================================
function formatSize(bytes) {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
}

function formatTime(isoString) {
    try {
        const d = new Date(isoString);
        const now = new Date();
        const diff = Math.floor((now - d) / 1000);
        if (diff < 60) return "刚刚";
        if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
        if (diff < 2592000) return `${Math.floor(diff / 86400)} 天前`;
        return d.toLocaleDateString("zh-CN");
    } catch {
        return isoString;
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// =========================================================
// 统计
// =========================================================
function updateStats(skills) {
    totalSkillsEl.textContent = skills.length;
    const fileCount = skills.reduce((sum, s) => sum + (s.file_count || 0), 0);
    totalFilesEl.textContent = fileCount;
    const tagSet = new Set();
    skills.forEach((s) => (s.tags || []).forEach((t) => tagSet.add(t)));
    totalTagsEl.textContent = tagSet.size;
}

// =========================================================
// 骨架屏
// =========================================================
function renderSkeletons() {
    skeletonGrid.innerHTML = "";
    for (let i = 0; i < 6; i++) {
        const card = document.createElement("div");
        card.className = "skeleton-card";
        card.innerHTML = `
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
        `;
        skeletonGrid.appendChild(card);
    }
}

// =========================================================
// 获取技能列表
// =========================================================
async function fetchSkills() {
    renderSkeletons();
    loading.style.display = "block";
    errorState.style.display = "none";
    emptyState.style.display = "none";
    skillsGrid.innerHTML = "";

    try {
        const res = await fetch(`${API_BASE}/api/skills`);
        if (!res.ok) throw new Error(`请求失败 (${res.status})`);
        allSkills = await res.json();
        updateStats(allSkills);
        renderSkills(allSkills);
    } catch (err) {
        errorMessage.textContent = `获取技能列表失败: ${err.message}`;
        errorState.style.display = "block";
        loading.style.display = "none";
    }
}

// =========================================================
// 渲染技能卡片
// =========================================================
function renderSkills(skills) {
    loading.style.display = "none";
    skillsGrid.innerHTML = "";

    if (skills.length === 0) {
        emptyState.style.display = "block";
        return;
    }
    emptyState.style.display = "none";
    updateStats(allSkills);

    skills.forEach((skill, index) => {
        const card = document.createElement("div");
        card.className = "skill-card";

        const fileInfo = skill.file_count > 1
            ? `${skill.file_count} 个文件`
            : (skill.file_size_readable || formatSize(skill.file_size));

        const tagsHtml = (skill.tags || [])
            .map((t) => `<span class="skill-tag">${escapeHtml(t)}</span>`)
            .join("");

        const authorName = skill.author || "匿名旅人";
        const versionCount = Array.isArray(skill.versions) ? skill.versions.length : 1;

        card.innerHTML = `
            <div class="skill-card-header">
                <h3>${escapeHtml(skill.name)}</h3>
                <span class="skill-size">${fileInfo}</span>
            </div>
            <p class="skill-desc">${escapeHtml(skill.description || "暂无描述")}</p>
            <div class="skill-tags">${tagsHtml || '<span class="skill-tag" style="opacity:0.4;">无标签</span>'}</div>
            <div class="skill-author-row">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
                <span class="skill-author-label">作者</span>
                <span class="skill-author-name">${escapeHtml(authorName)}</span>
            </div>
            <div class="skill-meta">
                <span class="skill-time">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                    </svg>
                    ${formatTime(skill.upload_time)}
                </span>
                <div class="skill-meta-actions">
                    <button class="btn btn-ghost btn-sm history-btn" data-id="${skill.id}" data-name="${escapeHtml(skill.name)}" title="查看历史版本">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><polyline points="3 3 3 8 8 8"/><polyline points="12 7 12 12 15 14"/>
                        </svg>
                        v${versionCount}
                    </button>
                    <button class="btn btn-primary btn-sm download-btn" data-id="${skill.id}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        下载
                    </button>
                </div>
            </div>
        `;

        skillsGrid.appendChild(card);
        setTimeout(() => card.classList.add("visible"), index * 60);
    });

    document.querySelectorAll(".download-btn").forEach((btn) => {
        btn.addEventListener("click", () => downloadSkill(btn.dataset.id));
    });
    document.querySelectorAll(".history-btn").forEach((btn) => {
        btn.addEventListener("click", () => openVersionModal(btn.dataset.id, btn.dataset.name));
    });
}

// =========================================================
// 搜索
// =========================================================
function filterSkills() {
    const q = searchInput.value.trim().toLowerCase();
    if (!q) {
        renderSkills(allSkills);
        searchClear.classList.remove("visible");
        return;
    }
    searchClear.classList.add("visible");
    const filtered = allSkills.filter(
        (s) =>
            s.name.toLowerCase().includes(q) ||
            (s.description || "").toLowerCase().includes(q) ||
            (s.tags || []).some((t) => t.toLowerCase().includes(q))
    );
    renderSkills(filtered);
}

searchClear.addEventListener("click", () => {
    searchInput.value = "";
    searchClear.classList.remove("visible");
    renderSkills(allSkills);
    searchInput.focus();
});

let searchTimer;
searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(filterSkills, 250);
});

// =========================================================
// 下载技能
// =========================================================
function downloadSkill(skillId) {
    const a = document.createElement("a");
    a.href = `${API_BASE}/api/skills/${skillId}/download`;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// =========================================================
// 模态框
// =========================================================
function openModal() {
    uploadForm.reset();
    uploadProgress.style.display = "none";
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 5v14M5 12h14"/>
        </svg>
        上传
    `;
    fileList.innerHTML = "";
    descCountEl.textContent = "0";
    modalOverlay.classList.add("active");
    document.body.style.overflow = "hidden";
}

function closeModal() {
    modalOverlay.classList.remove("active");
    document.body.style.overflow = "";
}

uploadBtn.addEventListener("click", openModal);
modalClose.addEventListener("click", closeModal);
cancelBtn.addEventListener("click", closeModal);
modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) closeModal();
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modalOverlay.classList.contains("active")) {
        closeModal();
    }
});

// =========================================================
// 文件选择
// =========================================================
fileInput.addEventListener("change", () => {
    fileList.innerHTML = "";
    if (fileInput.files.length > 0) {
        const f = fileInput.files[0];
        // Show file info
        fileZone.querySelector(".file-zone-text").textContent = f.name;
        fileZone.querySelector(".file-zone-hint").textContent = formatSize(f.size);

        const chip = document.createElement("span");
        chip.className = "file-chip";
        chip.textContent = `${f.name} (${formatSize(f.size)})`;
        fileList.appendChild(chip);
    } else {
        fileZone.querySelector(".file-zone-text").textContent = "将 .zip 文件拖放到此处，或点击选择";
        fileZone.querySelector(".file-zone-hint").textContent = "技能文件夹打包为 .zip，大小不超过 50MB";
    }
});

// 描述字数
descEl.addEventListener("input", () => {
    descCountEl.textContent = descEl.value.length;
});

// =========================================================
// 上传技能
// =========================================================
uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("skillName").value.trim();
    const description = descEl.value.trim();
    const tags = document.getElementById("skillTags").value.trim();

    if (!fileInput.files.length) {
        showToast("请选择一个 .zip 文件", "error");
        return;
    }

    const file = fileInput.files[0];
    if (!file.name.toLowerCase().endsWith(".zip")) {
        showToast("仅支持 .zip 格式的压缩包", "error");
        return;
    }

    if (file.size > 50 * 1024 * 1024) {
        showToast("文件大小超过 50MB 限制", "error");
        return;
    }

    if (!name) {
        showToast("请输入技能名称", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", name);
    formData.append("description", description);
    formData.append("tags", tags);

    uploadProgress.style.display = "flex";
    submitBtn.disabled = true;
    submitBtn.innerHTML = "上传中…";

    try {
        const xhr = new XMLHttpRequest();

        const result = await new Promise((resolve, reject) => {
            xhr.upload.addEventListener("progress", (evt) => {
                if (evt.lengthComputable) {
                    const pct = Math.round((evt.loaded / evt.total) * 100);
                    progressFill.style.width = `${pct}%`;
                    progressText.textContent = `${pct}%`;
                }
            });

            xhr.addEventListener("load", () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    try {
                        const detail = JSON.parse(xhr.responseText).detail || `上传失败 (${xhr.status})`;
                        reject(new Error(detail));
                    } catch {
                        reject(new Error(`上传失败 (${xhr.status})`));
                    }
                }
            });

            xhr.addEventListener("error", () => reject(new Error("网络错误")));
            xhr.addEventListener("abort", () => reject(new Error("上传已取消")));

            xhr.open("POST", `${API_BASE}/api/skills/upload`);
            xhr.send(formData);
        });

        showToast(`"${result.skill.name}" 上传成功！`);
        closeModal();
        await fetchSkills();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        uploadProgress.style.display = "none";
        progressFill.style.width = "0%";
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 5v14M5 12h14"/>
            </svg>
            上传
        `;
    }
});

// =========================================================
// 历史版本弹窗
// =========================================================
async function openVersionModal(skillId, skillName) {
    versionModalTitle.textContent = `历史版本·${skillName}`;
    versionModalSubtitle.textContent = "正在加载版本列表…";
    versionList.innerHTML = "";
    versionLoading.style.display = "block";
    versionModalOverlay.classList.add("active");
    document.body.style.overflow = "hidden";

    try {
        const res = await fetch(`${API_BASE}/api/skills/${skillId}/versions`);
        if (!res.ok) throw new Error(`请求失败 (${res.status})`);
        const data = await res.json();
        const versions = data.versions || [];
        renderVersions(skillId, versions);
        versionModalSubtitle.textContent = `共 ${versions.length} 个版本，最多保留 10 个历史版本`;
    } catch (err) {
        versionModalSubtitle.textContent = `加载失败: ${err.message}`;
        versionList.innerHTML = "";
    } finally {
        versionLoading.style.display = "none";
    }
}

function renderVersions(skillId, versions) {
    versionList.innerHTML = "";
    if (!versions.length) {
        versionList.innerHTML = `<li class="version-empty">暂无历史版本</li>`;
        return;
    }
    versions.forEach((v, idx) => {
        const isLatest = idx === 0; // 后端按时间降序
        const tagsHtml = (v.tags || [])
            .map((t) => `<span class="skill-tag">${escapeHtml(t)}</span>`)
            .join("");
        const li = document.createElement("li");
        li.className = "version-item";
        li.innerHTML = `
            <div class="version-item-head">
                <div class="version-item-title">
                    <span class="version-index">#${versions.length - idx}</span>
                    ${isLatest ? '<span class="version-latest-badge">最新</span>' : ''}
                </div>
                <div class="version-item-meta">
                    <span>作者 · ${escapeHtml(v.author || "匿名旅人")}</span>
                    <span>${formatTime(v.upload_time)}</span>
                </div>
            </div>
            ${v.description ? `<p class="version-desc">${escapeHtml(v.description)}</p>` : ""}
            ${tagsHtml ? `<div class="skill-tags">${tagsHtml}</div>` : ""}
            <div class="version-item-foot">
                <div class="version-item-info">
                    <span>${v.file_count || 0} 个文件</span>
                    <span>${v.file_size_readable || formatSize(v.file_size || 0)}</span>
                    <code class="version-md5" title="ZIP MD5">${(v.md5 || "").slice(0, 10)}</code>
                </div>
                <button class="btn btn-secondary btn-sm version-download" data-skill="${skillId}" data-version="${v.id}">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    下载此版本
                </button>
            </div>
        `;
        versionList.appendChild(li);
    });

    versionList.querySelectorAll(".version-download").forEach((btn) => {
        btn.addEventListener("click", () => {
            downloadSkillVersion(btn.dataset.skill, btn.dataset.version);
        });
    });
}

function downloadSkillVersion(skillId, versionId) {
    const a = document.createElement("a");
    a.href = `${API_BASE}/api/skills/${skillId}/versions/${versionId}/download`;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function closeVersionModal() {
    versionModalOverlay.classList.remove("active");
    document.body.style.overflow = "";
}

versionModalClose.addEventListener("click", closeVersionModal);
versionModalOverlay.addEventListener("click", (e) => {
    if (e.target === versionModalOverlay) closeVersionModal();
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && versionModalOverlay.classList.contains("active")) {
        closeVersionModal();
    }
});

// =========================================================
// 初始化
// =========================================================
fetchSkills();
