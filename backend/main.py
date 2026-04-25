import asyncio
import io
import os
import json
import uuid
import shutil
import zipfile
import time
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
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


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    安全中间件：
    1. 限流 — 同一 IP 30 秒内最多请求 10 次
    2. 并发 — 最多同时处理 2 个请求
    """
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
# 元数据结构归一化（兼容新旧格式）
# ---------------------------------------------------------------------------
def normalize_skill(skill: dict) -> dict:
    """将旧格式（单文件）自动升级为新格式（files 数组）"""
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
# API: 下载技能（直接返回存储的 ZIP）
# ---------------------------------------------------------------------------
@app.get("/api/skills/{skill_id}/download")
async def download_skill(skill_id: str):
    """根据 skill_id 返回该技能对应的 ZIP 包下载。"""
    skills = [normalize_skill(s) for s in load_metadata()]
    skill = next((s for s in skills if s["id"] == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    zip_path = FILES_DIR / f"{skill_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="技能文件已被删除")

    # 对中文文件名做 RFC 5987 编码
    ascii_name = skill["name"].encode("ascii", "replace").decode("ascii")
    if ascii_name == skill["name"]:
        filename = f"{skill['name']}.zip"
    else:
        filename = f"{ascii_name}.zip"

    return FileResponse(
        path=str(zip_path),
        filename=filename,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; '
                f"filename*=UTF-8''{quote(f'{skill["name"]}.zip')}"
            )
        },
    )


# ---------------------------------------------------------------------------
# API: 上传共享技能（仅接受 ZIP）
# ---------------------------------------------------------------------------
@app.post("/api/skills/upload")
async def upload_skill(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
):
    """
    上传并共享一个技能。

    - `file`: 技能文件夹打包后的 .zip 压缩包（保留目录结构）
    - `name`: 技能名称
    - `description`: 技能描述（可选）
    - `tags`: 标签，多个标签以英文逗号分隔（可选）
    - 文件大小不能超过 50MB
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="请选择一个文件")

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 .zip 压缩包格式")

    skill_id = str(uuid.uuid4())
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

    # 直接保存原 ZIP（目录结构完整保留）
    zip_path = FILES_DIR / f"{skill_id}.zip"
    with open(zip_path, "wb") as f:
        f.write(zip_content)

    tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    skills = load_metadata()

    # 同名覆盖：删除旧的 skill 文件和记录
    existing = [s for s in skills if s["name"] == name]
    for old in existing:
        old_zip = FILES_DIR / f"{old['id']}.zip"
        if old_zip.exists():
            old_zip.unlink()
        skills.remove(old)

    metadata = {
        "id": skill_id,
        "name": name,
        "description": description,
        "tags": tags_list,
        "files": file_infos,
        "file_count": len(file_infos),
        "file_size": raw_size,
        "file_size_readable": format_size(raw_size),
        "upload_time": datetime.now().isoformat(),
    }

    skills.append(metadata)
    save_metadata(skills)

    return {"message": "上传成功", "skill": metadata}


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
