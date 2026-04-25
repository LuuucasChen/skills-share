# 技能共享平台 — 生产部署指南

> 部署方式：systemd + Nginx（Ubuntu 22.04 LTS）  
> 内置安全：并发限制 2、IP 限流 30 秒  
> 代码仓库：https://github.com/LuuucasChen/skills-share

---

## 环境要求

- **系统**：Ubuntu 22.04 LTS（或其他 systemd 发行版）
- **Python**：3.11+（服务器已预装）
- **内存**：最低 512MB，推荐 1GB
- **带宽**：按实际访问需求
- **端口**：安全组需开放 `22`(SSH)、`80`(HTTP)；有域名时额外开放 `443`(HTTPS)

---

## 1. 从 GitHub 拉取代码到服务器

```bash
cd /opt
sudo git clone https://github.com/LuuucasChen/skills-share.git skills_share
sudo chown -R www-data:www-data skills_share
```

> **无域名部署说明**：没有购买域名时，直接用服务器**公网 IP** 访问即可。Nginx 配置中 `server_name _;` 已兼容 IP 直接访问。后续如需绑定域名，修改 `deploy/nginx.conf` 中的 `server_name` 并配置 HTTPS 即可。

---

## 2. 安装 Python 依赖

```bash
cd /opt/skills_share

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r backend/requirements.txt
```

---

## 3. 配置 systemd 服务

```bash
# 复制服务文件
sudo cp deploy/skills-share.service /etc/systemd/system/

# 重新加载并启动
sudo systemctl daemon-reload
sudo systemctl enable skills-share
sudo systemctl start skills-share

# 查看状态
sudo systemctl status skills-share
```

---

## 4. 安装并配置 Nginx

```bash
sudo apt update
sudo apt install nginx -y

# 复制站点配置
sudo cp deploy/nginx.conf /etc/nginx/sites-available/skills-share
sudo ln -sf /etc/nginx/sites-available/skills-share /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 检查配置并重启
sudo nginx -t
sudo systemctl restart nginx
```

---

## 5. 配置 HTTPS（有域名时可选）

> 如果没有域名，**跳过此步骤**，直接用 `http://<服务器公网IP>` 访问。

```bash
sudo apt install certbot python3-certbot-nginx -y

# 替换为你的域名
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

**无域名时 Nginx 已配置为 HTTP 模式**，通过 `server_name _;` 接受任意主机头（包括 IP 直接访问）。

---

## 6. 防火墙配置

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
# 有域名并配置 HTTPS 时再开放 443
# sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 7. 安全限制说明

代码已内置两层安全防护（`backend/main.py`）：

| 限制 | 值 | 说明 |
|------|-----|------|
| **并发限制** | 2 | 同一时刻最多处理 2 个请求，超出返回 `503` |
| **IP 限流** | 30 秒 | 同一 IP 30 秒内只能调用一次，超出返回 `429` |
| **上传限制** | 50 MB | 单个 ZIP 文件上限 |

如需调整，修改 `backend/main.py`：

```python
MAX_CONCURRENT_REQUESTS = 2       # 修改并发数
RATE_LIMIT_SECONDS = 30           # 修改限流间隔（秒）
```

---

## 8. 备份策略

```bash
# 创建备份目录
sudo mkdir -p /opt/backups

# 手动备份
sudo tar czf /opt/backups/skills-share-$(date +%Y%m%d).tar.gz /opt/skills_share/backend/storage/

# 添加定时任务（每天凌晨 3 点备份）
crontab -e
# 添加以下行：
0 3 * * * tar czf /opt/backups/skills-share-$(date +\%Y\%m\%d).tar.gz /opt/skills_share/backend/storage/ && find /opt/backups -name "*.tar.gz" -mtime +7 -delete
```

---

## 9. 日常运维

```bash
# 查看服务状态
sudo systemctl status skills-share

# 查看实时日志
sudo journalctl -u skills-share -f

# 重启服务
sudo systemctl restart skills-share

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 10. 故障排查

| 现象 | 排查方法 |
|------|----------|
| 页面无法访问 | `sudo systemctl status skills-share nginx` |
| 上传失败 | 检查 `client_max_body_size` 是否 ≥ 55M |
| 提示"请求过于频繁" | 这是正常的限流保护，等待 30 秒 |
| 提示"服务器并发已满" | 当前有 2 个请求在处理中，稍后再试 |
| 静态文件 404 | 确认项目目录下有 `frontend/` 文件夹 |

---

## 目录结构（服务器端）

```
/opt/skills_share/
├── backend/
│   ├── main.py              # FastAPI 主程序
│   ├── requirements.txt     # Python 依赖
│   └── storage/             # 数据持久化目录
│       ├── metadata.json    # 技能元数据
│       └── files/           # ZIP 文件存储
├── frontend/                # 前端静态文件
│   ├── index.html
│   ├── style.css
│   └── app.js
├── games/                   # 游戏模块
│   └── tetris/
├── deploy/                  # 部署配置
│   ├── skills-share.service
│   └── nginx.conf
└── DEPLOY.md               # 本文档
```

---

## 快速验证清单

- [ ] 代码已上传到 `/opt/skills_share`
- [ ] 虚拟环境已创建，依赖已安装
- [ ] `backend/storage/` 目录存在且可写
- [ ] systemd 服务已启用并运行
- [ ] Nginx 已安装并配置正确
- [ ] 防火墙已开放 80（有域名时再开 443）
- [ ] （可选）有域名时配置 HTTPS 证书
- [ ] 备份策略已配置
