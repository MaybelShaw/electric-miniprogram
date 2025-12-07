# 部署文档

## 概述
- 服务组成：后端 `Django + DRF`、商户前端 `Vite + React`、数据库 `PostgreSQL 17`、反向代理 `Nginx`。
- Compose 文件：开发 `docker-compose.dev.yaml`，生产 `docker-compose.prod.yaml`。
- Nginx 配置：`deploy/nginx.conf`，转发 `/api` 到后端，提供静态资源，并将 `/merchant/admin` 与 `/merchant/support` 通过重写交由前端 SPA 处理。

## 前置准备
- 安装 Docker Desktop（或兼容的 Docker 环境）。
- 开放本机端口：`80`（生产 Nginx）、`8000`（开发后端）、`3001`（开发前端）、`5432`（开发数据库）。
- 生产环境准备域名与 TLS 证书（建议在网关层终止 TLS）。

## 开发环境部署
1. 启动：
   ```bash.
   docker compose -f docker-compose.dev.yaml up -d
   ```
2. 访问：
   - 后端：`http://localhost:8000`
   - 前端：`http://localhost:3001`
3. 数据库迁移（如需手动）：
   ```bash
   docker compose -f docker-compose.dev.yaml exec backend uv run python manage.py migrate
   ```
4. 说明：开发模式使用 `backend.settings.development`（`backend/manage.py:9`），并通过 `DJANGO_DB=postgres` 切换到 Postgres（`backend/backend/settings/env_config.py:215`）。

## 生产环境部署
1. 替换 Compose 中的占位变量（强烈建议改为环境变量或使用 `--env-file`）：
   - 必填变量见 `backend/backend/settings/env_config.py:246-260`，包括 `SECRET_KEY/ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS/POSTGRES_*`、`WECHAT_*`、`YLH_*`。
2. 启动：
   ```bash
   docker compose -f docker-compose.prod.yaml up -d
   ```
3. 首次初始化（已自动执行）与手动执行：
   ```bash
   docker compose -f docker-compose.prod.yaml exec backend uv run python manage.py migrate
   docker compose -f docker-compose.prod.yaml exec backend uv run python manage.py collectstatic --noinput
   ```
4. 创建超级管理员（更安全的方式）：
   - 交互式创建（推荐）：
     ```bash
     docker compose -f docker-compose.prod.yaml exec backend uv run python manage.py createsuperuser
     ```
   - 一次性创建（避免在 Compose 中写入凭证）：
     - 使用临时环境变量运行一次命令，不将 `DJANGO_SUPERUSER_*` 写入配置文件或仓库：
       ```bash
       docker compose -f docker-compose.prod.yaml exec \
         -e DJANGO_SUPERUSER_USERNAME=admin \
         -e DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com \
         -e DJANGO_SUPERUSER_PASSWORD='your-strong-password' \
         backend uv run python manage.py createsuperuser --noinput
       ```
     - 或使用外部 `--env-file`（文件不入库且妥善保管），执行一次后删除该文件。
4. 访问：
   - 统一入口：`http://localhost`
   - 管理入口：`http://localhost/merchant/admin`
   - 客服入口：`http://localhost/merchant/support`
   - 后端 API：`http://localhost/api/`
5. Nginx 路由（`deploy/nginx.conf`）：
   - `/api/` → `backend:8000`（`deploy/nginx.conf:6-11`）
   - `/merchant/admin` → 重写为 `/admin`，由前端 SPA 处理（`deploy/nginx.conf:13-15`）
   - `/merchant/support` → 重写为 `/support`，由前端 SPA 处理（`deploy/nginx.conf:16-18`）
   - `/static/` → 后端静态目录（`deploy/nginx.conf:35-37`）
   - `/` → 商户前端构建产物（`deploy/nginx.conf:39-42`）

## 环境变量说明
- 开发最小集：
  - `DJANGO_ENV=development`
  - `DJANGO_DB=postgres`
  - `POSTGRES_DB=electric_dev`
  - `POSTGRES_USER=electric`
  - `POSTGRES_PASSWORD=electric`
  - `POSTGRES_HOST=db`
  - `POSTGRES_PORT=5432`
- 生产最小集（按需扩展）：
  - `DJANGO_ENV=production`
  - `DJANGO_SETTINGS_MODULE=backend.settings.production`
  - `SECRET_KEY`（强随机）
  - `ALLOWED_HOSTS`（逗号分隔）
  - `CORS_ALLOWED_ORIGINS`（逗号分隔，含前端域名）
  - `POSTGRES_DB/USER/PASSWORD/HOST/PORT`
  - `WECHAT_APPID/WECHAT_SECRET`
  - `YLH_CLIENT_ID/YLH_CLIENT_SECRET/YLH_CALLBACK_APP_KEY/YLH_CALLBACK_SECRET`
  - `ORDER_PAYMENT_TIMEOUT_MINUTES`（未支付订单自动取消超时，默认 `10`）

## 数据库与运维
- 登录数据库：
  ```bash
  docker compose -f docker-compose.prod.yaml exec db psql -U electric -d electric_miniprogram
  ```
- 备份：
  ```bash
  docker compose -f docker-compose.prod.yaml exec db pg_dump -U electric electric_miniprogram > backup.sql
  ```
- 恢复：
  ```bash
  cat backup.sql | docker compose -f docker-compose.prod.yaml exec -T db psql -U electric -d electric_miniprogram
  ```
- 创建管理员：
  ```bash
  docker compose -f docker-compose.prod.yaml exec backend uv run python manage.py createsuperuser
  ```

## 常用命令
- 查看日志：
  ```bash
  docker compose -f docker-compose.prod.yaml logs -f nginx
  docker compose -f docker-compose.prod.yaml logs -f backend
  ```
- 重启服务：
  ```bash
  docker compose -f docker-compose.prod.yaml restart nginx backend
  ```
- 停止与清理：
  ```bash
  docker compose -f docker-compose.prod.yaml down
  docker compose -f docker-compose.dev.yaml down --volumes --remove-orphans --rmi all
  ```

## 常见问题
- CORS 报错：确保生产 `CORS_ALLOWED_ORIGINS` 包含前端域名（`backend/backend/settings/production.py:23-26`）。
- 强制 HTTPS：生产建议开启 `SECURE_SSL_REDIRECT=True`（当前示例为 `False`，方便本地 `http` 访问）。
- 数据库健康检查未通过：等待 `db` 的 `pg_isready` 通过后端再启动（Compose `depends_on` 已配置健康依赖）。
- 端口冲突：调整宿主映射或停止占用端口的进程。

## 安全建议
- 不在仓库或 Compose 中写入真实密钥与凭证，统一使用环境变量或 Secret 管理（如 `--env-file`、Docker/K8s Secrets）。
- 生产禁用调试（`DEBUG=False`）并严格设置 `ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS`（`backend/backend/settings/production.py:11, 23-26`）。
- 强制 HTTPS：启用 `SECURE_SSL_REDIRECT=True`、设置 HSTS（`production.py:17-21`），在 Nginx 层终止 TLS。
- 生产后端使用 WSGI/ASGI 服务器替代 `runserver`：
  - 添加依赖后使用示例命令（需在 `pyproject.toml` 添加 `gunicorn` 或 `uvicorn`）：
    - WSGI：`uv run gunicorn backend.wsgi:application -b 0.0.0.0:8000 --workers 3 --timeout 120`
    - ASGI：`uv run uvicorn backend.asgi:application --host 0.0.0.0 --port 8000 --workers 3`
- 数据库不对外暴露端口，仅容器网络访问；按需配置只读账号与最小权限。
- 上传大小限制与访问日志在 Nginx 层统一控制，并按需开启缓存与压缩。
- 超级用户创建采用交互式或一次性临时变量方式，避免将凭证写入 Compose。

## Nginx 启用 TLS 示例（参考）
```nginx
server {
  listen 80;
  server_name yourdomain.com;
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl;
  server_name yourdomain.com;
  client_max_body_size 20m;
  ssl_certificate /etc/nginx/certs/fullchain.pem;
  ssl_certificate_key /etc/nginx/certs/privkey.pem;

  # 后端 API
  location /api/ {
    proxy_pass http://backend:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  # 前端路由重写
  location ^~ /merchant/admin {
    rewrite ^/merchant/admin(.*)$ /admin$1 last;
  }
  location ^~ /merchant/support {
    rewrite ^/merchant/support(.*)$ /support$1 last;
  }

  # 静态与 SPA
  location /static/ { alias /var/www/backend/staticfiles/; }
  location / { root /usr/share/nginx/html; try_files $uri /index.html; }
}
```
