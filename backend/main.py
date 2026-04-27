import asyncio
import io
import os
import json
import uuid
import shutil
import zipfile
import hashlib
import time
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_AUTHOR = "匿名旅人"  # 上传时未提供作者名的密即默认展示名
MAX_VERSIONS = 10               # 每个技能最多保留的历史版本数

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# 应用配置
# ---------------------------------------------------------------------------
app = FastAPI(title="技能共享平台", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 安全防护：限流 + 并发控制
# ---------------------------------------------------------------------------
MAX_CONCURRENT_REQUESTS = 2       # 最多同时处理 2 个请求
RATE_LIMIT_WINDOW = 30            # 限流时间窗口（秒）
RATE_LIMIT_COUNT = 10             # 每个 IP 在窗口内最多请求次数

request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
ip_access_log: dict[str, list[float]] = {}

# Markdown 文档接口独立限流（与全局限流互不干扰）
MD_RATE_LIMIT_WINDOW = 60
MD_RATE_LIMIT_COUNT  = 10
md_ip_access_log: dict[str, list[float]] = {}

# 白名单：仅允许在线读取的 Markdown 文件，防止路径穿越
ALLOWED_MD_FILES = {
    "selfhub-upload-skill.md",
    "selfhub-download-skill.md",
    "selfhub-install-skill.md",
    "selfhub-query-skills.md",
}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    安全中间件：
    1. 限流 — 同一 IP 30 秒内最多请求 10 次
    2. 并发 — 最多同时处理 2 个请求
    """
    # Markdown 文档接口走独立限流，跳过全局速率与并发控制
    if request.url.path.startswith("/api/markdown/"):
        response = await call_next(request)
        return response

    client_ip = request.client.host
    now = time.time()

    # 清理该 IP 的过期的访问记录
    log = ip_access_log.get(client_ip, [])
    log = [t for t in log if now - t < RATE_LIMIT_WINDOW]
    ip_access_log[client_ip] = log

    # 限流检查：窗口内请求数是否已达上限
    if len(log) >= RATE_LIMIT_COUNT:
        wait = int(RATE_LIMIT_WINDOW - (now - log[0]))
        return JSONResponse(
            status_code=429,
            content={"detail": f"请求过于频繁，请 {wait} 秒后再试"}
        )

    log.append(now)

    # 并发限制
    if request_semaphore.locked():
        return JSONResponse(
            status_code=503,
            content={"detail": "服务器并发已满，请稍后再试"}
        )

    async with request_semaphore:
        response = await call_next(request)
        return response

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "backend" / "storage"
FILES_DIR = STORAGE_DIR / "files"
METADATA_FILE = STORAGE_DIR / "metadata.json"
FRONTEND_DIR = BASE_DIR / "frontend"
GAMES_DIR = BASE_DIR / "games"
PLATFORM_SKILLS_DIR = BASE_DIR / "platform_skills"  # 平台原生技能文档目录

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB 总上传限制

# 确保存储目录存在
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
FILES_DIR.mkdir(parents=True, exist_ok=True)
if not METADATA_FILE.exists():
    METADATA_FILE.write_text("[]", encoding="utf-8")


# ---------------------------------------------------------------------------
# 数据读写（JSON 文件存储）
# ---------------------------------------------------------------------------
def load_metadata() -> list[dict]:
    """读取 metadata.json"""
    return json.loads(METADATA_FILE.read_text(encoding="utf-8"))


def save_metadata(data: list[dict]) -> None:
    """写入 metadata.json，确保原子性"""
    tmp = METADATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.move(str(tmp), str(METADATA_FILE))


def format_size(bytes_: int) -> str:
    """将字节数转为可读格式"""
    if bytes_ >= 1024 * 1024:
        return f"{bytes_ / 1024 / 1024:.1f} MB"
    if bytes_ >= 1024:
        return f"{bytes_ / 1024:.1f} KB"
    return f"{bytes_} B"


# ---------------------------------------------------------------------------
# 并发锁：按 skill name 细粒度锁，保证同名 skill 上传串行化
# ---------------------------------------------------------------------------
_upload_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()
_download_count_lock = asyncio.Lock()          # 保护下载计数写入


async def get_upload_lock(name: str) -> asyncio.Lock:
    async with _locks_guard:
        if name not in _upload_locks:
            _upload_locks[name] = asyncio.Lock()
        return _upload_locks[name]


# ---------------------------------------------------------------------------
# 元数据结构归一化（兼容旧格式）
# ---------------------------------------------------------------------------
def normalize_skill(skill: dict) -> dict:
    """
    将旧格式记录升级为带 versions 的新格式。
    新格式：顶层字段为最新版，`versions` 为历史版本列表（含最新版，按时间升序）。
    """
    # 旧版：单文件 -> files 数组
    if "files" not in skill:
        old_filename = skill.pop("filename", "")
        old_original = skill.pop("original_filename", "")
        old_size = skill.pop("file_size", 0)
        skill["files"] = [
            {
                "filename": old_filename,
                "original_filename": old_original,
                "file_size": old_size,
            }
        ] if old_filename else []
        skill["file_count"] = len(skill["files"])
        skill["file_size"] = old_size
        skill["file_size_readable"] = format_size(old_size)

    # 补全 author
    if not skill.get("author"):
        skill["author"] = DEFAULT_AUTHOR

    # 补全 md5（旧记录暂用空字符串，下次上传时会刷新）
    if "md5" not in skill:
        skill["md5"] = ""

    # 补全 download_count（旧记录默认 0）
    if "download_count" not in skill:
        skill["download_count"] = 0

    # 补全 versions（没有时将当前记录包装为单版本）
    if "versions" not in skill:
        skill["versions"] = [
            {
                "id": skill.get("id", str(uuid.uuid4())),
                "md5": skill.get("md5", ""),
                "author": skill.get("author", DEFAULT_AUTHOR),
                "description": skill.get("description", ""),
                "tags": skill.get("tags", []),
                "files": skill.get("files", []),
                "file_count": skill.get("file_count", 0),
                "file_size": skill.get("file_size", 0),
                "file_size_readable": skill.get("file_size_readable", format_size(skill.get("file_size", 0))),
                "upload_time": skill.get("upload_time", datetime.now().isoformat()),
            }
        ]
    return skill


# ---------------------------------------------------------------------------
# API: 查询技能
# ---------------------------------------------------------------------------
@app.get("/api/skills")
async def query_skills(q: Optional[str] = Query(None)):
    """
    查询已共享的技能列表。

    - `q` (可选): 关键字，对 name / description / tags 进行模糊匹配。
    """
    skills = [normalize_skill(s) for s in load_metadata()]
    if q:
        q = q.lower()
        skills = [
            s
            for s in skills
            if q in s["name"].lower()
            or q in s["description"].lower()
            or any(q in tag.lower() for tag in s["tags"])
        ]
    return skills


# ---------------------------------------------------------------------------
# 下载响应构造器
# ---------------------------------------------------------------------------
def _build_zip_response(zip_path: Path, skill_name: str) -> FileResponse:
    """下载响应构造器，兼容中文文件名（RFC 5987）。"""
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="技能文件已被删除")

    ascii_name = skill_name.encode("ascii", "replace").decode("ascii")
    filename = f"{skill_name}.zip" if ascii_name == skill_name else f"{ascii_name}.zip"
    encoded = quote(f"{skill_name}.zip")
    return FileResponse(
        path=str(zip_path),
        filename=filename,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; '
                f"filename*=UTF-8''{encoded}"
            )
        },
    )


# ---------------------------------------------------------------------------
# API: 下载技能（最新版）
# ---------------------------------------------------------------------------
@app.get("/api/skills/{skill_id}/download")
async def download_skill(skill_id: str):
    """根据 skill_id 返回最新版本的 ZIP 下载，并累加下载计数。"""
    skills = [normalize_skill(s) for s in load_metadata()]
    skill = next((s for s in skills if s["id"] == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    # 持久化累加下载计数
    async with _download_count_lock:
        raw = load_metadata()
        for s in raw:
            if s.get("id") == skill_id:
                s["download_count"] = s.get("download_count", 0) + 1
                save_metadata(raw)
                break

    return _build_zip_response(FILES_DIR / f"{skill_id}.zip", skill["name"])


# ---------------------------------------------------------------------------
# API: 技能历史版本列表
# ---------------------------------------------------------------------------
@app.get("/api/skills/{skill_id}/versions")
async def list_skill_versions(skill_id: str):
    """返回指定技能的历史版本列表（按 upload_time 降序）。"""
    skills = [normalize_skill(s) for s in load_metadata()]
    skill = next((s for s in skills if s["id"] == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    versions = sorted(
        skill.get("versions", []),
        key=lambda v: v.get("upload_time", ""),
        reverse=True,
    )
    return {"skill_id": skill["id"], "name": skill["name"], "versions": versions}


# ---------------------------------------------------------------------------
# API: 下载指定历史版本
# ---------------------------------------------------------------------------
@app.get("/api/skills/{skill_id}/versions/{version_id}/download")
async def download_skill_version(skill_id: str, version_id: str):
    """下载指定技能的指定历史版本。"""
    skills = [normalize_skill(s) for s in load_metadata()]
    skill = next((s for s in skills if s["id"] == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    version = next((v for v in skill.get("versions", []) if v["id"] == version_id), None)
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    # 持久化累加下载计数（计在顶层 skill 上）
    async with _download_count_lock:
        raw = load_metadata()
        for s in raw:
            if s.get("id") == skill_id:
                s["download_count"] = s.get("download_count", 0) + 1
                save_metadata(raw)
                break

    return _build_zip_response(FILES_DIR / f"{version_id}.zip", skill["name"])


# ---------------------------------------------------------------------------
# API: 上传共享技能（仅接受 ZIP）
# ---------------------------------------------------------------------------
@app.post("/api/skills/upload")
async def upload_skill(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    author: str = Form(""),
):
    """
    上传并共享一个技能。

    - `file`: 技能文件夹打包后的 .zip 压缩包（保留目录结构）
    - `name`: 技能名称
    - `description`: 技能描述（可选）
    - `tags`: 标签，多个标签以英文逗号分隔（可选）
    - `author`: 作者名，由当前 Agent 填入自己的名字（可选，默认 匿名旅人）
    - 文件大小不能超过 50MB

    行为说明：
    - 同名技能按 ZIP 的 MD5 判定：
      - 首次上传：新建记录
      - MD5 与最新版相同：幂等（仅刷新元数据）
      - MD5 不同：新增历史版本，超过 MAX_VERSIONS 时 FIFO 淘汰最旧版本
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="请选择一个文件")

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 .zip 压缩包格式")

    zip_content = await file.read()
    raw_size = len(zip_content)

    if raw_size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="文件大小超过 50MB 限制")

    # 验证 ZIP 并提取内部文件列表
    file_infos = []
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            bad = zf.testzip()
            if bad:
                raise HTTPException(status_code=400, detail=f"ZIP 文件已损坏: {bad}")
            for info in zf.infolist():
                if not info.is_dir():
                    file_infos.append({
                        "original_filename": info.filename,
                        "file_size": info.file_size,
                    })
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="上传的文件不是有效的 ZIP 压缩包")

    if not file_infos:
        raise HTTPException(status_code=400, detail="ZIP 文件中没有有效文件")

    md5 = hashlib.md5(zip_content).hexdigest()
    author_clean = (author or "").strip() or DEFAULT_AUTHOR
    tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    now_iso = datetime.now().isoformat()
    size_readable = format_size(raw_size)

    # 按 skill name 获取细粒度锁，保证同名串行化
    lock = await get_upload_lock(name)
    async with lock:
        skills = [normalize_skill(s) for s in load_metadata()]
        existing = next((s for s in skills if s["name"] == name), None)

        is_new_version = False
        is_duplicate = False

        if existing is None:
            # 分支 1：不存在同名，新建
            skill_id = str(uuid.uuid4())
            version_id = skill_id
            with open(FILES_DIR / f"{version_id}.zip", "wb") as f:
                f.write(zip_content)

            version_record = {
                "id": version_id, "md5": md5, "author": author_clean,
                "description": description, "tags": tags_list, "files": file_infos,
                "file_count": len(file_infos), "file_size": raw_size,
                "file_size_readable": size_readable, "upload_time": now_iso,
            }
            skill = {
                "id": skill_id, "name": name, "md5": md5, "author": author_clean,
                "description": description, "tags": tags_list, "files": file_infos,
                "file_count": len(file_infos), "file_size": raw_size,
                "file_size_readable": size_readable, "upload_time": now_iso,
                "versions": [version_record],
            }
            skills.append(skill)
            is_new_version = True

        else:
            versions = existing.get("versions", [])
            latest_md5 = versions[-1].get("md5", "") if versions else existing.get("md5", "")

            if versions and latest_md5 == md5:
                # 分支 2：MD5 相同，幂等（不写磁盘、不新增版本）
                latest = versions[-1]
                latest["author"] = author_clean
                latest["description"] = description
                latest["tags"] = tags_list
                latest["upload_time"] = now_iso
                existing["author"] = author_clean
                existing["description"] = description
                existing["tags"] = tags_list
                existing["upload_time"] = now_iso
                skill = existing
                is_duplicate = True
            else:
                # 分支 3：MD5 不同，新增历史版本
                version_id = str(uuid.uuid4())
                with open(FILES_DIR / f"{version_id}.zip", "wb") as f:
                    f.write(zip_content)

                version_record = {
                    "id": version_id, "md5": md5, "author": author_clean,
                    "description": description, "tags": tags_list, "files": file_infos,
                    "file_count": len(file_infos), "file_size": raw_size,
                    "file_size_readable": size_readable, "upload_time": now_iso,
                }
                versions.append(version_record)

                # FIFO 淘汰最旧版本
                while len(versions) > MAX_VERSIONS:
                    oldest = versions.pop(0)
                    old_zip = FILES_DIR / f"{oldest['id']}.zip"
                    if old_zip.exists():
                        try:
                            old_zip.unlink()
                        except OSError:
                            pass

                # 顶层字段同步（id 指向最新版）
                existing["id"] = version_id
                existing["md5"] = md5
                existing["author"] = author_clean
                existing["description"] = description
                existing["tags"] = tags_list
                existing["files"] = file_infos
                existing["file_count"] = len(file_infos)
                existing["file_size"] = raw_size
                existing["file_size_readable"] = size_readable
                existing["upload_time"] = now_iso
                existing["versions"] = versions
                skill = existing
                is_new_version = True

        save_metadata(skills)

    return {
        "message": "上传成功",
        "skill": skill,
        "is_new_version": is_new_version,
        "is_duplicate": is_duplicate,
    }


# ---------------------------------------------------------------------------
# API: 在线读取平台原生技能文档（Markdown）
# ---------------------------------------------------------------------------
@app.get("/api/markdown/{filename}")
async def get_markdown(filename: str, request: Request):
    """
    返回平台原生技能文档的 Markdown 原文。

    - 白名单限制，仅允许读取 4 个平台技能文档，防止路径穿越
    - 独立限流：同一 IP 60 秒内最多请求 10 次
    """
    # 独立限流
    client_ip = request.client.host
    now = time.time()
    log = md_ip_access_log.get(client_ip, [])
    log = [t for t in log if now - t < MD_RATE_LIMIT_WINDOW]
    if len(log) >= MD_RATE_LIMIT_COUNT:
        wait = int(MD_RATE_LIMIT_WINDOW - (now - log[0]))
        raise HTTPException(
            status_code=429,
            detail=f"文档请求过于频繁，请 {wait} 秒后再试"
        )
    log.append(now)
    md_ip_access_log[client_ip] = log

    # 白名单校验
    if filename not in ALLOWED_MD_FILES:
        raise HTTPException(status_code=404, detail="文档不存在")

    md_path = PLATFORM_SKILLS_DIR / filename
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="文档文件未找到")

    content = md_path.read_text(encoding="utf-8")
    return PlainTextResponse(
        content,
        headers={"Content-Type": "text/markdown; charset=utf-8"},
    )


# ---------------------------------------------------------------------------
# 托管前端与游戏静态文件（必须在 API 路由之后挂载）
# ---------------------------------------------------------------------------
if GAMES_DIR.exists():
    app.mount("/games", StaticFiles(directory=str(GAMES_DIR), html=True), name="games")

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
