---
name: selfhub-setup
description: 一键安装 Skills Share 平台全套技能包（upload / download / install / query 共 4 个技能），安装完成后 Agent 即可上传、查询、下载和安装共享平台中的技能。
---

# selfhub-setup — 平台技能包一键安装指南

> 下载本文档后，按照以下步骤操作，即可为当前 Agent 安装 Skills Share 平台的全套技能包。

## 包含技能

| 技能名                   | 用途                                   |
|--------------------------|----------------------------------------|
| selfhub-upload-skill     | 将本地 ZIP 包上传到技能共享平台        |
| selfhub-download-skill   | 下载平台上的技能 ZIP 包到本地          |
| selfhub-install-skill    | 下载并解压技能，直接部署到 skills 目录 |
| selfhub-query-skills     | 查询平台上已有的技能列表               |

## 安装步骤

### 第一步：下载全部 4 个技能文档

依次下载以下 4 个 `.md` 文件：

```
http://43.139.218.65/api/markdown/selfhub-upload-skill.md
http://43.139.218.65/api/markdown/selfhub-download-skill.md
http://43.139.218.65/api/markdown/selfhub-install-skill.md
http://43.139.218.65/api/markdown/selfhub-query-skills.md
```

### 第二步：放入 skills 目录

将下载的 4 个 `.md` 文件放入当前 Agent 的 skills 目录。

常见路径：
- Qoder IDE：`~/.qoder/skills/`
- 或工作区根目录下的 `skills/` 文件夹

示例（PowerShell）：

```powershell
$skillsDir = "$env:USERPROFILE\.qoder\skills"
New-Item -ItemType Directory -Force -Path $skillsDir

$base = "http://43.139.218.65/api/markdown"
@(
    "selfhub-upload-skill.md",
    "selfhub-download-skill.md",
    "selfhub-install-skill.md",
    "selfhub-query-skills.md"
) | ForEach-Object {
    Invoke-WebRequest -Uri "$base/$_" -OutFile "$skillsDir\$_"
    Write-Host "已安装: $_"
}
```

示例（bash / curl）：

```bash
SKILLS_DIR="$HOME/.qoder/skills"
mkdir -p "$SKILLS_DIR"
BASE="http://43.139.218.65/api/markdown"

for f in selfhub-upload-skill.md selfhub-download-skill.md selfhub-install-skill.md selfhub-query-skills.md; do
    curl -sSL "$BASE/$f" -o "$SKILLS_DIR/$f"
    echo "已安装: $f"
done
```

### 第三步：重载技能

重启 IDE 或重新加载 Agent，4 个技能即生效，可通过以下方式调用：

- 上传技能到平台：调用 `selfhub-upload-skill`
- 查询平台技能列表：调用 `selfhub-query-skills`
- 下载平台技能：调用 `selfhub-download-skill`
- 安装平台技能到本地：调用 `selfhub-install-skill`

## 验证安装

安装完成后，可让 Agent 执行以下查询验证平台连通性：

```
GET http://43.139.218.65/api/skills
```

正常返回 JSON 数组即表示安装成功、平台可访问。

## 注意事项

- 每个 IP 每 60 秒最多请求文档接口 10 次，请勿频繁重复下载
- 文档为只读接口，不需要鉴权
- 如遇 404 请检查文件名拼写是否正确
