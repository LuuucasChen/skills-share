---
name: query-skills
description: 查询技能共享平台上的技能列表，支持关键字模糊搜索。
---

# query-skills

查询技能共享平台上的技能列表。支持通过关键字对技能名称、描述、标签进行模糊搜索。

## 用法

调用 `GET /api/skills?q={keyword}` 接口。

### 请求示例

```
GET http://localhost:8000/api/skills?q=python
GET http://localhost:8000/api/skills
```

### 响应示例

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Python 自动化脚本",
    "description": "一键自动化处理日常任务的 Python 脚本合集",
    "tags": ["python", "自动化", "脚本"],
    "files": [
      {
        "filename": "550e8400-auto_script.py",
        "original_filename": "auto_script.py",
        "file_size": 1024
      },
      {
        "filename": "550e8400-SKILLS.md",
        "original_filename": "SKILLS.md",
        "file_size": 512
      }
    ],
    "file_count": 2,
    "file_size": 1536,
    "file_size_readable": "1.5 KB",
    "upload_time": "2026-04-25T10:30:00"
  }
]
```

## 注意事项

- `q` 参数可选，不传则返回全部技能
- 搜索不区分大小写
- 返回按上传时间降序排列
