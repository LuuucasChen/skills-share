---
name: selfhub-upload-skill
description: 向技能共享平台上传并共享一个技能，需将技能文件夹打包为 .zip 后调用接口。
---

# selfhub-upload-skill

向技能共享平台上传并共享一个技能。上传前需将技能文件夹打包为 `.zip` 压缩包，上传后原 ZIP 被直接存储，原始目录结构完整保留。

## 用法

调用 `POST /api/skills/upload` 接口，使用 `multipart/form-data` 格式提交。

### 请求参数

| 参数          | 类型   | 必填 | 说明                                   |
|---------------|--------|------|----------------------------------------|
| `file`        | File   | 是   | 技能文件夹打包的 .zip 压缩包，≤ 50MB    |
| `name`        | String | 是   | 技能名称                               |
| `description` | String | 否   | 技能描述                               |
| `tags`        | String | 否   | 标签，多个标签用英文逗号分隔           |

### 请求示例（curl）

```bash
curl -X POST http://localhost:8000/api/skills/upload \
  -F "file=@./my-skill.zip" \
  -F "name=My Awesome Skill" \
  -F "description=这是一个很棒的技能" \
  -F "tags=python,自动化,工具"
```


### 响应示例

```json
{
  "message": "上传成功",
  "skill": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Awesome Skill",
    "description": "这是一个很棒的技能",
    "tags": ["python", "自动化", "工具"],
    "files": [
      {
        "original_filename": "SKILL.md",
        "file_size": 1024
      },
      {
        "original_filename": "scripts/auto.py",
        "file_size": 2048
      }
    ],
    "file_count": 2,
    "file_size": 3072,
    "file_size_readable": "3.0 KB",
    "upload_time": "2026-04-25T12:00:00"
  }
}
```

## 注意事项

- 上传的文件必须是 `.zip` 格式，否则返回 400 错误
- 上传的 ZIP 会被直接存储，下载时原样返回，原始目录结构完整保留
- 文件大小不能超过 50MB
- 技能名称不能为空
