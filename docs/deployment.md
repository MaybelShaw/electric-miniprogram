# 部署文档

## 概述
- 服务组成：后端 `Django + DRF`、商户前端 `Vite + React`、数据库 `PostgreSQL 17`、反向代理 `Nginx`。
- Compose 文件：开发 `docker-compose.dev.yaml`，预发布 `docker-compose.preprod.yaml`，生产 `docker-compose.prod.yaml`。
- Nginx 配置：`deploy/nginx.conf`，转发 `/api` 到后端，提供静态资源，并将 `/merchant/admin` 与 `/merchant/support` 通过重写交由前端 SPA 处理。

## 前置准备
- 安装 Docker Desktop（或兼容的 Docker 环境）。
- 开放本机端口：`80`（生产 Nginx）、`8000`（开发后端）、`3001`（开发前端）、`5432`（开发数据库）。
 - 准备外部环境变量文件（本地示例）：`/Users/bobo/.envs/electric-miniprogram/.env.production`；服务器推荐：`/etc/electric-miniprogram/.env.production`（文件不入库，权限受控）。
- 生产环境准备域名与 TLS 证书（建议在网关层终止 TLS）。

## 开发环境部署
1. 启动：
   ```bash.
   docker compose -f docker-compose.dev.yaml up -d
   ```
2. 代码更新后的生效方式（服务器开发环境常见）：
   - 拉取代码后，前端容器一般会自动热更新；若浏览器仍看到旧行为，可执行 `docker compose -f docker-compose.dev.yaml restart merchant`。
   - 后端代码更新后建议执行 `docker compose -f docker-compose.dev.yaml restart backend`；如涉及迁移再补充运行 `migrate`。
3. 访问：
   - 后端：`http://localhost:8000`
   - 前端：`http://localhost:3001`
4. 数据库迁移（如需手动）：
   ```bash
   docker compose -f docker-compose.dev.yaml exec backend uv run python manage.py migrate
   ```
5. 说明：开发模式使用 `backend.settings.development`（`backend/manage.py:9`），并通过 `DJANGO_DB=postgres` 切换到 Postgres（`backend/backend/settings/env_config.py:215`）。

## 生产环境部署
1. 准备外部 `env_file`：`/etc/electric-miniprogram/.env.production`
   - 必填变量见 `backend/backend/settings/env_config.py:246-260`，包括 `SECRET_KEY/ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS/POSTGRES_*`、`WECHAT_*`、`YLH_*`。
   - 将 `docker-compose.prod.yaml:23-24` 的 `env_file` 更新为服务器路径：
     ```yaml
     env_file:
       - /etc/electric-miniprogram/.env.production
     ```
   - 示例（占位值需替换为真实生产值）：
     ```env
     DJANGO_ENV=production
     DJANGO_SETTINGS_MODULE=backend.settings.production
     SECRET_KEY=your-strong-secret
     ALLOWED_HOSTS=www.qxelectric.cn,qxelectric.cn,cdn.qxelectric.cn,origin.qxelectric.cn
     CORS_ALLOWED_ORIGINS=https://www.qxelectric.cn,https://qxelectric.cn
     POSTGRES_DB=electric_miniprogram
     POSTGRES_USER=electric
     POSTGRES_PASSWORD=electric
     POSTGRES_HOST=db
     POSTGRES_PORT=5432
     WECHAT_APPID=...
     WECHAT_SECRET=...
     YLH_CLIENT_ID=...
     YLH_CLIENT_SECRET=...
     YLH_CALLBACK_APP_KEY=...
     YLH_CALLBACK_SECRET=...
     ORDER_PAYMENT_TIMEOUT_MINUTES=10
     SECURE_SSL_REDIRECT=True
     ```
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
  - 外部 `env_file` 路径（本地示例）：`/Users/bobo/.envs/electric-miniprogram/.env.production`（`docker-compose.prod.yaml:23-24`、`docker-compose.preprod.yaml:23-29`）
  - 服务器推荐路径：`/etc/electric-miniprogram/.env.production`（请更新 Compose 中的 `env_file`）

## 预发布环境部署
1. 使用与生产相同的外部 `env_file`：`/etc/electric-miniprogram/.env.production`
2. 启动：
   ```bash
   docker compose -f docker-compose.preprod.yaml up -d
   ```
3. 差异覆盖：
   - `ALLOWED_HOSTS` 包含 `localhost,127.0.0.1`（`docker-compose.preprod.yaml:26`）
   - `CORS_ALLOWED_ORIGINS` 使用 `http`（`docker-compose.preprod.yaml:27`）
  - `SECURE_SSL_REDIRECT=false`（`docker-compose.preprod.yaml:29`）

## Ubuntu 24.04 LTS 服务器部署
1. 系统准备：
   ```bash
   sudo apt update
   sudo apt install -y ca-certificates curl gnupg
   ```
2. 安装 Docker Engine 与 Compose 插件（官方源）：
   ```bash
   # 添加 Docker GPG 密钥
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   sudo chmod a+r /etc/apt/keyrings/docker.gpg

   # 添加 APT 源（Ubuntu 24.04 = noble）
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

   # 非 root 用户使用 docker
   sudo usermod -aG docker $USER
   newgrp docker

   # 开机自启
   sudo systemctl enable docker
   ```
3. 防火墙（如启用 `ufw`）：
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp  # 如启用 TLS
   sudo ufw reload
   ```
4. 代码与环境文件：
   ```bash
   # 放置仓库（示例路径）
   cd /opt && sudo mkdir -p electric-miniprogram && sudo chown -R $USER:$USER electric-miniprogram
   git clone <your-repo-url> /opt/electric-miniprogram

   # 准备外部 env_file（权限受控）
   sudo mkdir -p /etc/electric-miniprogram
   sudo nano /etc/electric-miniprogram/.env.production
   sudo chmod 600 /etc/electric-miniprogram/.env.production
   sudo chown root:root /etc/electric-miniprogram/.env.production
   ```
5. 更新 Compose 的 `env_file`（在仓库中）：
   - 修改 `docker-compose.prod.yaml:23-24` 与 `docker-compose.preprod.yaml:23-29` 为：
     ```yaml
     env_file:
       - /etc/electric-miniprogram/.env.production
     ```
6. 启动与验证：
   ```bash
   cd /opt/electric-miniprogram
   docker compose -f docker-compose.prod.yaml up -d
   docker compose -f docker-compose.prod.yaml logs -f nginx
   ```
7. 证书与支付密钥（可选）：
   - 微信支付私钥与公钥建议放置于：`/etc/electric-miniprogram/certs/wechat/`，并在外部 `env_file` 中更新路径。
   - 如需在容器内使用，可在 Compose 为 `backend` 添加只读卷挂载并将路径改为容器内路径，参考文档的 TLS 示例与卷挂载做法。

> 说明：Compose 已设置 `restart: unless-stopped`，在 Docker 服务启动后会自动拉起容器；数据库健康检查保证后端在 Postgres 就绪后再启动。

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
- 不在仓库或 Compose 中写入真实密钥与凭证，统一使用环境变量或 Secret 管理（外部 `env_file`、Docker/K8s Secrets）。
- Compose 通过外部 `env_file` 加载变量：`docker-compose.prod.yaml:23-24`、`docker-compose.preprod.yaml:23-29`。
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

## 升级指南
- 升级原则：先在预发布环境验证，再进行生产升级；每次升级前备份数据库，升级后进行健康检查与日志核对。

### 预发布验证（推荐）
- 步骤：
  - 更新代码与依赖（如需）：在仓库中拉取最新代码；如有新依赖，预发布的 `backend` 重启时会自动执行 `uv sync` 与迁移（`docker-compose.preprod.yaml:34-38`）。
  - 重建前端产物：`docker compose -f docker-compose.preprod.yaml restart merchant-build`
  - 重启后端并执行迁移与静态收集：`docker compose -f docker-compose.preprod.yaml restart backend`
  - 查看日志：`docker compose -f docker-compose.preprod.yaml logs -f backend`
  - 健康检查（容器内）：`docker compose -f docker-compose.preprod.yaml exec backend curl -s http://127.0.0.1:8000/healthz`
  - 前端验证：访问预发布入口，确认主要页面与功能可用。

### 生产升级（最小停机流程）
- 1. 备份数据库：
  ```bash
  docker compose -f docker-compose.prod.yaml exec -T db pg_dump -U electric electric_miniprogram > backup-$(date +%F-%H%M).sql
  ```
- 2. 重建前端构建产物（不影响服务）：
  ```bash
  docker compose -f docker-compose.prod.yaml restart merchant-build
  ```
- 3. 重启后端（自动依赖安装、迁移与静态收集）：
  ```bash
  docker compose -f docker-compose.prod.yaml restart backend
  ```
- 4. 如有 Nginx 配置变更，重启 Nginx：
  ```bash
  docker compose -f docker-compose.prod.yaml restart nginx
  ```
- 5. 验证：
  ```bash
  docker compose -f docker-compose.prod.yaml logs -f backend
  docker compose -f docker-compose.prod.yaml exec backend curl -s http://127.0.0.1:8000/healthz
  curl -I http://localhost/api/
  ```

### 环境变量与证书变更
- 外部 `env_file` 更新后需要重启后端：
  - 服务器路径：`/etc/electric-miniprogram/.env.production`
  - 执行：`docker compose -f docker-compose.prod.yaml restart backend`
- 微信支付证书与密钥：
  - 建议存放：`/etc/electric-miniprogram/certs/wechat/`
  - 更新 `.env.production` 中路径，并按需为 `backend` 添加只读卷挂载后重启。

### 回滚策略
- 若升级后出现异常：
  - 回滚代码到上一版本（Git 或文件回退）。
  - 重启后端与前端构建容器：
    ```bash
    docker compose -f docker-compose.prod.yaml restart backend merchant-build
    ```
  - 如数据库迁移导致问题，使用备份文件恢复：
    ```bash
    cat backup-<timestamp>.sql | docker compose -f docker-compose.prod.yaml exec -T db psql -U electric -d electric_miniprogram
    ```

### 版本与镜像
- 基础镜像：`python:3.12-slim`、`node:20-alpine`、`nginx:alpine`；建议定期执行 `docker compose pull` 以获取安全更新。
- 后端与前端代码通过宿主目录挂载（`./backend:/app`、`./merchant:/app`），升级主要通过代码变更与容器重启完成。
