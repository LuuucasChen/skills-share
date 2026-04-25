---
name: selfhub-install-skill
description: 从技能共享平台下载指定技能的 ZIP 包，并自动解压安装到本地 skills 目录。
---

# selfhub-install-skill

从技能共享平台下载指定技能的 ZIP 压缩包，**自动解压并将所有文件安装到 skills 目录**。适用于"技能共享平台安装 xxx 技能"场景，安装后的文件可直接作为 Agent Skill 使用。

## 用法

### 前置步骤

1. 先调用 `selfhub-query-skills` 获取技能列表，确认目标技能存在
2. 从返回结果中提取目标技能的 `id` 字段和 `name` 字段
3. 确认该技能包含对 Agent 有用的文件（如 `.md` 格式的 skill 文件或可执行脚本）

### 执行安装

调用 `GET /api/skills/{skill_id}/download` 接口获取 ZIP，然后解压到指定目录。

### 请求示例

```
GET http://43.139.218.65/api/skills/550e8400-e29b-41d4-a716-446655440000/download
```

### 响应

返回 ZIP 文件流（`application/zip`），ZIP 内包含该技能下的所有原始文件。

## 安装步骤

1. 调用 `selfhub-query-skills` 获取技能列表
2. 从返回结果中提取目标技能的 `id` 和 `name` 字段
3. 调用下载接口 `GET /api/skills/{id}/download` 获取 ZIP 数据
4. 在 `platform_skills/` 下创建以技能名称命名的子目录（如 `platform_skills/{技能名称}/`）
5. 解压 ZIP 中的所有文件到该子目录
6. 对于解压出的 `.md` 文件，确认其符合 Agent Skill 格式（含 frontmatter），即可被当前 Agent 识别和调用

### 安装目录结构示例

安装 "自动化部署技能" 后，目录结构如下：

```
~\skills\
└── deploy\           # 新安装的技能目录
    ├── SKILLS.md            # 技能定义文件（可被 Agent 识别）
    ├── deploy.sh            # 可执行脚本
    └── config.yaml          # 配置文件
```

## 下载 vs 安装

- **下载（selfhub-download-skill）**：仅将 ZIP 保存到 skills 目录，不解压
- **安装（本技能）**：下载 ZIP 后自动解压，将内含文件部署到 skills 目录

## 注意事项

- 安装前请确保磁盘空间充足
- 安装后的 `.md` 文件如果符合 Skill 规范（含 `name` 和 `description` frontmatter），Agent 可直接使用
- 如果目标目录已存在同名技能，会覆盖已有文件
- 如果技能已被删除，下载接口返回 404
