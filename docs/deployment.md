# 部署文档

## 概述
- 服务组成：后端 `Django + DRF`、商户前端 `Vite + React`、数据库 `PostgreSQL 17`、反向代理 `Nginx`。
- Compose 文件：开发 `docker/docker-compose.dev.yaml`，预发布 `docker/docker-compose.preprod.yaml`，生产 `docker/docker-compose.prod.yaml`。
- Nginx 配置：`deploy/nginx.conf`，转发 `/api` 到后端，提供静态资源，并将 `/merchant/admin` 与 `/merchant/support` 通过重写交由前端 SPA 处理。

## 前置准备
- 安装 Docker Desktop（或兼容的 Docker 环境）。
- 开放本机端口：`80`（生产 Nginx）、`8000`（开发后端）、`3001`（开发前端）、`5432`（开发数据库）。
 - 准备外部环境变量文件（本地示例）：`/Users/bobo/.envs/electric-miniprogram/.env.production`；服务器推荐：`/etc/electric-miniprogram/.env.production`（文件不入库，权限受控）。
- 生产环境准备域名与 TLS 证书（建议在网关层终止 TLS）。

## 开发环境部署
1. 启动：
   ```bash.
   docker compose -f docker/docker-compose.dev.yaml up -d
   ```
   Windows / Docker Desktop 首次启动或修改 `docker/Dockerfile.backend.dev` 后，建议显式重建后端开发镜像：
   ```bash
   docker compose -f docker/docker-compose.dev.yaml up -d --build backend
   ```
2. 代码更新后的生效方式（服务器开发环境常见）：
   - 拉取代码后，前端容器一般会自动热更新；若浏览器仍看到旧行为，可执行 `docker compose -f docker/docker-compose.dev.yaml restart merchant`。
   - 后端代码更新后建议执行 `docker compose -f docker/docker-compose.dev.yaml restart backend`；如涉及迁移再补充运行 `migrate`。
3. 访问：
   - 后端：`http://localhost:8000`
   - 前端：`http://localhost:3001`
4. 数据库迁移（如需手动）：
   ```bash
   docker compose -f docker/docker-compose.dev.yaml exec backend .venv/bin/python manage.py migrate
   ```
5. 说明：开发模式使用 `backend.settings.development`（`backend/manage.py:9`），并通过 `DJANGO_DB=postgres` 切换到 Postgres（`backend/backend/settings/env_config.py:215`）。开发后端镜像由 `docker/Dockerfile.backend.dev` 构建并内置 `uv`；启动依赖 Compose 的 `db` 健康检查，随后执行 `uv sync`、迁移、开发超级管理员创建和 `runserver`。测试数据、测试商品和销量重算不再随后端容器启动自动执行；如需演示数据，需要另行准备脚本或通过后台/API 创建。
6. 本地微信支付联调：
   - 将微信支付私钥、公钥或平台证书放到仓库外的安全来源后，复制到本地 `certs/wechatpay/`；该目录除 `.gitkeep` 外已被 `.gitignore` 忽略。
   - 在 `backend/.env` 写入本地联调变量，证书路径使用容器内路径 `/etc/electric-miniprogram/certs/wechatpay/...`，例如 `WECHAT_PAY_PRIVATE_KEY_PATH=/etc/electric-miniprogram/certs/wechatpay/apiclient_key.pem`。
   - `docker/docker-compose.dev.yaml` 会只读挂载 `certs/wechatpay`，并可通过 `ELECTRIC_DEV_ENV_FILE` 指向其他本地 env 文件；默认仍保留 `SKIP_WECHAT_PAY_CONFIG_CHECK=1`，允许未配置微信支付时启动开发后端。
   - 首次加入证书或修改 Compose 挂载后，仅 `restart backend` 不会刷新容器挂载，需执行 `docker compose -f docker/docker-compose.dev.yaml up -d --force-recreate backend`。
   - `WECHAT_PAY_NOTIFY_URL` 和 `WECHAT_PAY_REFUND_NOTIFY_URL` 不能保留 `https://your.domain/...`，真实联调需填写微信可访问的 HTTPS 公网地址（例如内网穿透域名）并指向 `/api/payments/callback/wechat/`、`/api/payments/refund-callback/wechat/`。

## 生产环境部署
> 生产 Compose 已改为镜像化部署：后端依赖在 `docker/Dockerfile.backend.prod` 的 build 阶段通过 `uv sync --frozen --no-dev` 安装；商户后台在独立的 `docker/Dockerfile.merchant.prod` build 阶段通过 `npm ci && npm run build` 构建，并在运行时把产物复制到 `merchant_dist` 卷；Nginx 镜像只包含 `deploy/nginx.conf`，并只读挂载 `merchant_dist`。运行阶段不再执行 `pip install uv`、`uv sync`、`npm install`，也不再挂载后端或商户后台源码目录。

1. 准备外部 `env_file`：`/etc/electric-miniprogram/.env.production`
   - 必填变量见 `backend/backend/settings/env_config.py:246-260`，包括 `SECRET_KEY/ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS/POSTGRES_*`、`WECHAT_*`、`YLH_*`。
   - 将 `docker/docker-compose.prod.yaml:23-24` 的 `env_file` 更新为服务器路径：
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
     POSTGRES_USER=<database-user>
     POSTGRES_PASSWORD=<strong-database-password>
     POSTGRES_HOST=db
     POSTGRES_PORT=5432
     WECHAT_APPID=...
     WECHAT_SECRET=...
    YLH_CLIENT_ID=...
    YLH_CLIENT_SECRET=...
    YLH_CALLBACK_APP_KEY=...
    YLH_CALLBACK_SECRET=...
    YLH_SOURCE_SYSTEM=skwl
    YLH_SHOP_NAME=默认店铺
    ORDER_PAYMENT_TIMEOUT_MINUTES=1440
     SECURE_SSL_REDIRECT=True
     ```
2. 启动：
   ```bash
   docker compose -f docker/docker-compose.prod.yaml build backend nginx merchant-build
   docker compose -f docker/docker-compose.prod.yaml up -d
   ```
3. 首次初始化（已自动执行）与手动执行：
   ```bash
   docker compose -f docker/docker-compose.prod.yaml exec backend .venv/bin/python manage.py migrate
   docker compose -f docker/docker-compose.prod.yaml exec backend .venv/bin/python manage.py collectstatic --noinput
   ```
4. 创建超级管理员（更安全的方式）：
   - 交互式创建（推荐）：
     ```bash
     docker compose -f docker/docker-compose.prod.yaml exec backend .venv/bin/python manage.py createsuperuser
     ```
   - 一次性创建（避免在 Compose 中写入凭证）：
     - 使用临时环境变量运行一次命令，不将 `DJANGO_SUPERUSER_*` 写入配置文件或仓库：
       ```bash
       docker compose -f docker/docker-compose.prod.yaml exec \
         -e DJANGO_SUPERUSER_USERNAME=admin \
         -e DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com \
         -e DJANGO_SUPERUSER_PASSWORD='your-strong-password' \
         backend .venv/bin/python manage.py createsuperuser --noinput
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
6. 持久化目录：
   - PostgreSQL 数据仍使用 Compose 命名卷 `postgres_data`，兼容原有数据库数据。
   - Django 静态文件使用 Compose 命名卷 `staticfiles`，由后端 `collectstatic` 写入并由 Nginx 只读挂载。
   - 商户后台构建产物使用 Compose 命名卷 `merchant_dist`，由 `merchant-build` 写入并由 Nginx 只读挂载。
   - 生产上传媒体文件沿用旧目录，挂载宿主机项目内 `backend/backend/media` 到容器 `/app/backend/media`，Nginx 通过 `/media/` 只读访问，避免历史上传图片迁移。

## 环境变量说明
- 开发最小集：
  - `DJANGO_ENV=development`
  - `DJANGO_DB=postgres`
  - `POSTGRES_DB=electric_dev`
  - `POSTGRES_USER=electric`
  - `POSTGRES_PASSWORD=electric`
  - `POSTGRES_HOST=db`
  - `POSTGRES_PORT=5432`
  - `SKIP_WECHAT_PAY_CONFIG_CHECK=1`（仅开发 Compose 使用，允许未配置微信支付证书时启动本地后端；生产不要设置）
- 开发微信支付联调变量（按需写入 `backend/.env` 或 `ELECTRIC_DEV_ENV_FILE` 指向的文件）：
  - `WECHAT_APPID/WECHAT_SECRET`
  - `WECHAT_PAY_MCHID/WECHAT_PAY_SERIAL_NO/WECHAT_PAY_API_V3_KEY`
  - `WECHAT_PAY_PRIVATE_KEY_PATH=/etc/electric-miniprogram/certs/wechatpay/...`
  - `WECHAT_PAY_PUBLIC_KEY_PATH` 或 `WECHAT_PAY_PLATFORM_CERT_PATH`，路径同样使用容器内 `/etc/electric-miniprogram/certs/wechatpay/...`
  - `WECHAT_PAY_NOTIFY_URL/WECHAT_PAY_REFUND_NOTIFY_URL`
- 生产最小集（按需扩展）：
  - `DJANGO_ENV=production`
  - `DJANGO_SETTINGS_MODULE=backend.settings.production`
  - `SECRET_KEY`（强随机）
  - `ALLOWED_HOSTS`（逗号分隔）
  - `CORS_ALLOWED_ORIGINS`（逗号分隔，含前端域名）
  - `POSTGRES_DB/USER/PASSWORD/HOST/PORT`
  - `WECHAT_APPID/WECHAT_SECRET`
  - `YLH_CLIENT_ID/YLH_CLIENT_SECRET/YLH_CALLBACK_APP_KEY/YLH_CALLBACK_SECRET`
- `ORDER_PAYMENT_TIMEOUT_MINUTES`（未支付订单自动取消超时，默认 `1440`，即 24 小时）
  - 外部 `env_file` 路径（本地示例）：`/Users/bobo/.envs/electric-miniprogram/.env.production`（`docker/docker-compose.prod.yaml:23-24`、`docker/docker-compose.preprod.yaml:23-29`）
  - 服务器推荐路径：`/etc/electric-miniprogram/.env.production`（请更新 Compose 中的 `env_file`）
- 生产/预发 `db` 和 `backend` 服务均从外部 `env_file` 读取 `POSTGRES_*`；Compose 不再内置数据库用户名或密码。若 `postgres_data` 已经初始化，`.env.production` 中的 `POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD` 必须与现有数据库一致；修改这些变量不会自动修改已有数据库账号密码。

## 预发布环境部署
1. 使用与生产相同的外部 `env_file`：`/etc/electric-miniprogram/.env.production`
2. 启动：
   ```bash
   docker compose -f docker/docker-compose.preprod.yaml up -d
   ```
3. 差异覆盖：
   - `ALLOWED_HOSTS` 包含 `localhost,127.0.0.1`（`docker/docker-compose.preprod.yaml:26`）
   - `CORS_ALLOWED_ORIGINS` 使用 `http`（`docker/docker-compose.preprod.yaml:27`）
  - `SECURE_SSL_REDIRECT=false`（`docker/docker-compose.preprod.yaml:29`）
  - Nginx 使用 `deploy/nginx.preprod.conf`，仅监听 HTTP `80`，不加载生产 TLS 证书。

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
   - 修改 `docker/docker-compose.prod.yaml:23-24` 与 `docker/docker-compose.preprod.yaml:23-29` 为：
     ```yaml
     env_file:
       - /etc/electric-miniprogram/.env.production
     ```
6. 启动与验证：
   ```bash
   cd /opt/electric-miniprogram
   docker compose -f docker/docker-compose.prod.yaml up -d
   docker compose -f docker/docker-compose.prod.yaml logs -f nginx
   ```
7. 证书与支付密钥（可选）：
   - 微信支付私钥与公钥建议放置于：`/etc/electric-miniprogram/certs/wechatpay/`，并在外部 `env_file` 中更新路径。
   - 如需在容器内使用，可在 Compose 为 `backend` 添加只读卷挂载并将路径改为容器内路径，参考文档的 TLS 示例与卷挂载做法。

> 说明：Compose 已设置 `restart: unless-stopped`，在 Docker 服务启动后会自动拉起容器；数据库健康检查保证后端在 Postgres 就绪后再启动。

## 数据库与运维
- 登录数据库：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml exec db psql -U electric -d electric_miniprogram
  ```
- 备份数据库与媒体文件（推荐）：
  ```bash
  bash deploy/backup_production.sh
  ```
  默认生成到 `/var/backups/electric-miniprogram/<timestamp>/`，包含 `database.dump`、`media.tar.gz`、`manifest.txt`。
- 从备份回溯数据库与媒体文件：
  ```bash
  bash deploy/restore_production.sh /var/backups/electric-miniprogram/<timestamp> --yes
  ```
  恢复脚本会先停止 `backend/nginx/merchant-build`，清空 PostgreSQL `public` schema 后导入 `database.dump`，并把当前媒体目录移动到 `backend/backend/media.rollback-<timestamp>` 后再恢复备份媒体。
- 创建管理员：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml exec backend uv run python manage.py createsuperuser
  ```

## 常用命令
- 查看日志：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml logs -f nginx
  docker compose -f docker/docker-compose.prod.yaml logs -f backend
  ```
- 重启服务：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml restart nginx backend
  ```
- 停止与清理：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml down
  docker compose -f docker/docker-compose.dev.yaml down --volumes --remove-orphans --rmi all
  ```

## 常见问题
- CORS 报错：确保生产 `CORS_ALLOWED_ORIGINS` 包含前端域名（`backend/backend/settings/production.py:23-26`）。
- 强制 HTTPS：生产 Nginx 暴露 `80/443`，`80` 会返回 `301` 跳转到同域名 HTTPS；`backend.settings.production` 默认开启 `SECURE_SSL_REDIRECT=True`，并通过 `SECURE_PROXY_SSL_HEADER` 信任 Nginx 传入的 `X-Forwarded-Proto`。
- 数据库健康检查未通过：等待 `db` 的 `pg_isready` 通过后端再启动（Compose `depends_on` 已配置健康依赖）。
- 迁移时报 `constraint "unique_category_level_parent_name" of relation "catalog_category" does not exist`：更新到包含 `catalog.0037` 兼容修复的版本后重新构建并启动 `backend`。该迁移会幂等删除旧约束，并清理可能残留的同名唯一索引，随后继续添加店铺字段与新约束；重试前仍应先执行 `bash deploy/backup_production.sh`。
- 迁移时报 `relation "catalog_specialzone" already exists`：更新到包含 `catalog.0038` 兼容修复的版本后重新构建并启动 `backend`。该迁移会跳过已存在的动态专区表、字段、索引和约束，并补齐缺失对象，适用于表已存在但 `django_migrations` 未记录 `catalog.0038` 的生产库。
- 端口冲突：调整宿主映射或停止占用端口的进程。

## 安全建议
- 不在仓库或 Compose 中写入真实密钥与凭证，统一使用环境变量或 Secret 管理（外部 `env_file`、Docker/K8s Secrets）。
- Compose 通过外部 `env_file` 加载变量：`docker/docker-compose.prod.yaml:23-24`、`docker/docker-compose.preprod.yaml:23-29`。
- 生产禁用调试（`DEBUG=False`）并严格设置 `ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS`（`backend/backend/settings/production.py:11, 23-26`）。
- 强制 HTTPS：生产 Nginx 负责 `80 -> 443` 重定向与 TLS 终止；Django 保持 `SECURE_SSL_REDIRECT=True`、HSTS 与安全 Cookie 设置（`production.py:17-25`）。
- 生产后端使用 Gunicorn 替代 `runserver`；`backend/pyproject.toml` 已包含 `gunicorn`，生产/预发 Compose 当前启动命令为 `.venv/bin/gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 90 --access-logfile - --error-logfile -`，适合 2 核 4G 服务器作为初始配置。
- 生产排障日志默认应收紧：`.env.production` 建议显式设置 `WECHAT_PAY_DEBUG=False`、`INTEGRATIONS_API_DEBUG=False`、`INTEGRATIONS_CALLBACK_DEBUG=False`，只有短时间排障时再打开。
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
  - 更新代码：在仓库中拉取最新代码。
  - 构建预发布镜像：`docker compose -f docker/docker-compose.preprod.yaml build backend merchant-build`
  - 启动或更新预发布服务：`docker compose -f docker/docker-compose.preprod.yaml up -d`
  - 查看日志：`docker compose -f docker/docker-compose.preprod.yaml logs -f backend`
  - 健康检查（容器内）：`docker compose -f docker/docker-compose.preprod.yaml exec backend curl -s http://127.0.0.1:8000/healthz`
  - 前端验证：访问预发布入口，确认主要页面与功能可用。

### 生产升级（最小停机流程）
- 1. 备份数据库与媒体文件：
  ```bash
  bash deploy/backup_production.sh
  ```
- 2. 构建生产镜像：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml build backend nginx merchant-build
  ```
- 3. 启动新镜像（后端会执行迁移与静态收集，随后以 Gunicorn 启动）：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml up -d
  ```
- 4. 如有 Nginx 配置变更，重启 Nginx：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml restart nginx
  ```
- 5. 验证：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml logs -f backend
  docker compose -f docker/docker-compose.prod.yaml exec backend curl -s http://127.0.0.1:8000/healthz
  curl -I http://localhost/api/
  ```
- 只更新商户后台、不改 Nginx 配置时：
  ```bash
  docker compose -f docker/docker-compose.prod.yaml build merchant-build
  docker compose -f docker/docker-compose.prod.yaml up -d merchant-build
  ```
  `merchant-build` 会把新产物写入 `merchant_dist`，Nginx 继续读取同一个卷，通常不需要重启 Nginx。

### 环境变量与证书变更
- 外部 `env_file` 更新后需要重启后端：
  - 服务器路径：`/etc/electric-miniprogram/.env.production`
  - 执行：`docker compose -f docker/docker-compose.prod.yaml restart backend`
- 微信支付证书与密钥：
  - 生产/预发 Compose 已将宿主机 `/etc/electric-miniprogram/certs/wechatpay` 只读挂载到容器同路径。
  - `.env.production` 中的 `WECHAT_PAY_PRIVATE_KEY_PATH`、`WECHAT_PAY_PUBLIC_KEY_PATH` 或 `WECHAT_PAY_PLATFORM_CERT_PATH` 应指向容器内 `/etc/electric-miniprogram/certs/wechatpay/...`。
  - 微信支付分账复用同一套平台/主店商户号、API v3 密钥、私钥和公钥/平台证书；合作方店铺的 `wechat_mch_id` 只作为分账接收方商户号，不需要挂载合作方证书。

### 回滚策略
- 若升级后出现异常：
  - 回滚代码到上一版本（Git 或文件回退）。
  - 重新构建并启动上一版本镜像：
    ```bash
    docker compose -f docker/docker-compose.prod.yaml build backend nginx merchant-build
    docker compose -f docker/docker-compose.prod.yaml up -d
    ```
  - 如数据库迁移或媒体文件写入导致问题，使用备份快照恢复：
    ```bash
    bash deploy/restore_production.sh /var/backups/electric-miniprogram/<timestamp> --yes
    ```

### 版本与镜像
- 基础镜像：`python:3.12-slim`、`node:20-alpine`、`nginx:alpine`；建议定期执行 `docker compose pull` 以获取安全更新。
- 后端镜像由 `docker/Dockerfile.backend.prod` 构建，依赖锁定来自 `backend/uv.lock`。
- 商户后台产物镜像由 `docker/Dockerfile.merchant.prod` 构建，依赖锁定来自 `merchant/package-lock.json`，运行时只复制已构建的 `dist` 到 `merchant_dist`。
- Nginx 镜像由 `docker/Dockerfile.nginx.prod` 构建，只内置 `deploy/nginx.conf`，运行时只读挂载 `merchant_dist`。
- 生产运行容器不再挂载源码目录；只有证书、媒体文件、静态文件卷和商户后台产物卷在运行期挂载。

## 生产待处理事项优先级
- P0/P1：小程序生产 API 基址。生产构建必须显式设置 `TARO_APP_API_BASE_URL` 为线上 HTTPS API 域名；当前代码缺失该变量时会回退到 `http://127.0.0.1:8000/api`，上线前需修复为生产构建失败或 CI 强校验。
- P1：生产调试开关。生产 `.env.production` 应显式关闭 `WECHAT_PAY_DEBUG`、`INTEGRATIONS_API_DEBUG`、`INTEGRATIONS_CALLBACK_DEBUG`，后续代码应把这些开关默认值改为 `False`。

## 生产自检补充
- 上线前执行 `docker compose -f docker/docker-compose.prod.yaml exec backend .venv/bin/python manage.py check --deploy`；该检查会触发 drf-spectacular schema 生成，确保 `/api/schema/`、`/api/docs/` 的生产认证配置保持可用。
- `backend.settings.production` 强制开启 `SESSION_COOKIE_SECURE`、`CSRF_COOKIE_SECURE`、`X_FRAME_OPTIONS=DENY`；生产启动时会补回被 SimpleUI 移除的 `XFrameOptionsMiddleware`，确保 `check --deploy` 不再报告 cookie 与点击劫持防护缺口。
- 生产库应预先存在受控超级管理员；生产环境禁止通过匿名密码登录接口或 `reset_admin` 自动创建首个超级管理员。需要重置密码时，只对已有管理员执行 `reset_admin` 或使用交互式 `createsuperuser` 的受控运维流程。
