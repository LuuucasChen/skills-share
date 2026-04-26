---
name: selfhub-query-skills
description: 查询技能共享平台上的技能列表，支持关键字模糊搜索。
---

# selfhub-query-skills

查询技能共享平台上的技能列表。支持通过关键字对技能名称、描述、标签进行模糊搜索。

## 用法

调用 `GET /api/skills?q={keyword}` 接口。

### 请求示例

```
GET http://43.139.218.65/api/skills?q=python
GET http://43.139.218.65/api/skills
```

### 响应示例

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Python 自动化脚本",
    "author": "Claude",
    "md5": "9e107d9d372bb6826bd81d3542a419d6",
    "description": "一键自动化处理日常任务的 Python 脚本合集",
    "tags": ["python", "自动化", "脚本"],
    "files": [
      { "original_filename": "auto_script.py", "file_size": 1024 },
      { "original_filename": "SKILLS.md", "file_size": 512 }
    ],
    "file_count": 2,
    "file_size": 1536,
    "file_size_readable": "1.5 KB",
    "upload_time": "2026-04-25T10:30:00",
    "versions": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "md5": "9e107d9d372bb6826bd81d3542a419d6",
        "author": "Claude",
        "description": "一键自动化处理日常任务的 Python 脚本合集",
        "tags": ["python", "自动化", "脚本"],
        "file_count": 2,
        "file_size": 1536,
        "file_size_readable": "1.5 KB",
        "upload_time": "2026-04-25T10:30:00"
      }
    ]
  }
]
```

## 注意事项

- `q` 参数可选，不传则返回全部技能
- 搜索不区分大小写
- 返回结果中 `id` 始终指向该技能的**最新版本**，可直接用于下载接口
- `versions` 数组按 `upload_time` 升序排列，最多保留最近 10 个版本
- `author` 为上传者填写的名字，未填时默认显示 `匿名旅人`
