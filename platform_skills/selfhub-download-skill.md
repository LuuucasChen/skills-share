---
name: selfhub-download-skill
description: 从技能共享平台下载指定的技能 ZIP 包到本地 skills 目录，不解压。
---

# selfhub-download-skill

从技能共享平台下载指定技能的 ZIP 压缩包，**直接保存到本Agent的skills目录，不进行解压**。适用于"仅下载"场景，下载后的文件保持 ZIP 格式。

## 用法

调用 `GET /api/skills/{skill_id}/download` 接口，将返回的 ZIP 内容保存到 `platform_skills/{技能名称}.zip`。

### 请求示例

```
GET http://localhost:8000/api/skills/550e8400-e29b-41d4-a716-446655440000/download
```

### 响应

返回 ZIP 文件流（`application/zip`），文件名为 `{技能名称}.zip`。ZIP 内包含该技能下的所有原始文件。

## 操作步骤

1. 先调用 `selfhub-query-skills` 获取技能列表
2. 从返回结果中提取目标技能的 `id` 字段
3. 调用下载接口获取 ZIP 二进制数据
4. 将 ZIP 保存到 `Agent的skills目录/{技能名称}.zip`（不解压）

### 保存位置

```
d:\skills_share\platform_skills\{技能名称}.zip
```

## 下载 vs 安装

- **下载（本技能）**：仅将 ZIP 保存到 skills 目录，不解压
- **安装（selfhub-install-skill）**：下载 ZIP 后自动解压，将内含文件部署到 skills 目录

## 注意事项

- `skill_id` 必须是有效的 UUID
- 下载返回的是 ZIP 包，包含该技能下的所有文件
- 如果技能已被删除，返回 404
