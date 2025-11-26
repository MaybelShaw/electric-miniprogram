# 部署指南

## 环境准备

### 系统要求
- 操作系统：Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+
- Python：3.12+
- 数据库：PostgreSQL 13+ (生产环境) / SQLite (开发环境)
- 内存：最少2GB，推荐4GB+
- 磁盘：最少10GB可用空间

### 依赖软件
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv
sudo apt install postgresql postgresql-contrib
sudo apt install nginx
sudo apt install supervisor

# CentOS/RHEL
sudo yum install python310 python3-pip
sudo yum install postgresql-server postgresql-contrib
sudo yum install nginx
sudo yum install supervisor
```

## 测试环境部署（Staging）

### 策略与差异
- 环境标识：`DJANGO_ENV=production`（使用生产配置，关闭DEBUG）
- 允许域名：设置测试域名到 `ALLOWED_HOSTS`
- CORS：设置测试域名到 `CORS_ALLOWED_ORIGINS`
- 第三方API：启用模拟数据 `HAIER_USE_MOCK_DATA=true`，易理货/海尔走测试地址
- 数据库：独立的PostgreSQL实例与库，禁止对线上库的写入
- 证书：可配测试证书或公网有效证书

### 环境变量示例（.env.staging）
```env
DJANGO_SETTINGS_MODULE=backend.settings.production
DJANGO_ENV=production

# 安全与网络
SECRET_KEY=staging-secret-key-change-me
ALLOWED_HOSTS=staging.yourdomain.com
CORS_ALLOWED_ORIGINS=https://staging.yourdomain.com

# 数据库（生产配置要求使用POSTGRES_*变量）
POSTGRES_DB=electric_db_staging
POSTGRES_USER=electric_user
POSTGRES_PASSWORD=change_me
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# 第三方凭证（使用测试环境）
WECHAT_APPID=your_test_appid
WECHAT_SECRET=your_test_secret

# 海尔API（默认已指向测试域）
HAIER_CLIENT_ID=your_client_id
HAIER_CLIENT_SECRET=your_client_secret
HAIER_USE_MOCK_DATA=true

# 易理货（测试地址）
YLH_AUTH_URL=http://dev.ylhtest.com/ylh-cloud-mgt-auth-dev/oauth/token
YLH_BASE_URL=http://dev.ylhtest.com/ylh-cloud-service-jst-order-dev
YLH_USERNAME=
YLH_PASSWORD=
YLH_CLIENT_ID=open_api_erp
YLH_CLIENT_SECRET=12345678
```

## 生产环境部署

### 1. 克隆代码
```bash
cd /var/www
git clone https://github.com/yourrepo/electric-miniprogram.git
cd electric-miniprogram/backend
```

### 2. 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖
```bash
# 推荐：使用 uv（读取 pyproject.toml / uv.lock）
curl -Ls https://astral.sh/uv/install.sh | sh
uv venv .venv
source .venv/bin/activate
uv sync --frozen

# 备选：使用 pip（无锁定，基于 pyproject）
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### 4. 配置环境变量
```bash
cp .env.example .env
nano .env
```

**生产环境配置：**
```env
DJANGO_SETTINGS_MODULE=backend.settings.production
DJANGO_ENV=production

# 安全与网络
SECRET_KEY=prod-secret-key-change-me
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 数据库（使用POSTGRES_*变量，生产模式强校验）
POSTGRES_DB=electric_db
POSTGRES_USER=electric_user
POSTGRES_PASSWORD=change_me
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# 微信小程序（生产凭证）
WECHAT_APPID=
WECHAT_SECRET=

# 海尔API（生产域）
HAIER_CLIENT_ID=
HAIER_CLIENT_SECRET=
HAIER_TOKEN_URL=https://openplat-test.haier.net/oauth2/auth
HAIER_BASE_URL=https://openplat-test.haier.net
HAIER_CUSTOMER_CODE=
HAIER_SEND_TO_CODE=
HAIER_SUPPLIER_CODE=
HAIER_PASSWORD=
HAIER_SELLER_PASSWORD=
HAIER_USE_MOCK_DATA=false

# 易理货系统（生产地址）
YLH_AUTH_URL=
YLH_BASE_URL=
YLH_USERNAME=
YLH_PASSWORD=
YLH_CLIENT_ID=open_api_erp
YLH_CLIENT_SECRET=12345678
```

### 5. 数据库设置

#### PostgreSQL配置
```bash
# 切换到postgres用户
sudo -u postgres psql

# 创建数据库和用户
CREATE DATABASE electric_db;
CREATE USER electric_user WITH PASSWORD 'your_password';
ALTER ROLE electric_user SET client_encoding TO 'utf8';
ALTER ROLE electric_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE electric_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE electric_db TO electric_user;
\q
```

#### 执行迁移
```bash
python manage.py migrate
```

#### 创建超级用户
```bash
python manage.py createsuperuser
```

### 6. 收集静态文件
```bash
python manage.py collectstatic --noinput
```

### 7. 配置Gunicorn

**安装Gunicorn：**
```bash
pip install gunicorn
```

**创建Gunicorn配置文件：**
```bash
nano gunicorn_config.py
```

```python
# gunicorn_config.py
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 日志
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# 进程命名
proc_name = "electric_backend"

# 守护进程
daemon = False
```

**创建日志目录：**
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown -R $USER:$USER /var/log/gunicorn
```

### 8. 配置Supervisor

**创建Supervisor配置：**
```bash
sudo nano /etc/supervisor/conf.d/electric_backend.conf
```

```ini
[program:electric_backend]
command=/var/www/electric-miniprogram/backend/venv/bin/gunicorn backend.wsgi:application -c /var/www/electric-miniprogram/backend/gunicorn_config.py
directory=/var/www/electric-miniprogram/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/electric_backend.log
stderr_logfile=/var/log/supervisor/electric_backend_error.log
```

**启动Supervisor：**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start electric_backend
sudo supervisorctl status
```

### 9. 配置Nginx

**创建Nginx配置：**
```bash
sudo nano /etc/nginx/sites-available/electric_backend
```

```nginx
upstream electric_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 10M;

    # 静态文件
    location /static/ {
        alias /var/www/electric-miniprogram/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 媒体文件
    location /media/ {
        alias /var/www/electric-miniprogram/backend/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API请求
    location / {
        proxy_pass http://electric_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # 健康检查
    location /healthz {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

**启用站点：**
```bash
sudo ln -s /etc/nginx/sites-available/electric_backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 10. 配置SSL证书（Let's Encrypt）

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期
sudo certbot renew --dry-run
```

## Docker部署

### Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目元数据用于依赖安装
COPY pyproject.toml uv.lock ./

# 安装 uv 并同步依赖（锁定）
RUN curl -Ls https://astral.sh/uv/install.sh | sh && \
    /root/.local/bin/uv sync --frozen --no-dev

# 复制项目代码
COPY . .

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: electric_db
      POSTGRES_USER: electric_user
      POSTGRES_PASSWORD: your_password
    ports:
      - "5432:5432"

  backend:
    build: .
    command: gunicorn backend.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### 启动Docker容器
```bash
docker-compose up -d
docker-compose logs -f
```

## 日志配置

### 日志目录结构
```
logs/
├── django.log
├── error.log
├── access.log
└── integrations.log
```

### 日志轮转配置
```bash
sudo nano /etc/logrotate.d/electric_backend
```

```
/var/www/electric-miniprogram/backend/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        supervisorctl restart electric_backend
    endscript
}
```

## 监控和告警

### 健康检查
```bash
# 检查服务状态
curl http://localhost/healthz

# 检查数据库连接
python manage.py check --database default
```

### 性能监控
- 使用New Relic / Datadog
- 配置Prometheus + Grafana
- 使用Django Debug Toolbar（仅开发环境）

### 错误追踪
- 配置Sentry
- 监控错误日志
- 设置告警规则

## 备份策略

### 数据库备份
```bash
# 创建备份脚本
nano /usr/local/bin/backup_db.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/electric_db"
mkdir -p $BACKUP_DIR

# 备份数据库
pg_dump -U electric_user electric_db > $BACKUP_DIR/backup_$DATE.sql

# 压缩备份
gzip $BACKUP_DIR/backup_$DATE.sql

# 删除30天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

```bash
chmod +x /usr/local/bin/backup_db.sh

# 添加到crontab
crontab -e
0 2 * * * /usr/local/bin/backup_db.sh
```

### 媒体文件备份
```bash
# 同步到远程存储
rsync -avz /var/www/electric-miniprogram/backend/media/ user@backup-server:/backups/media/
```

## 更新部署

### 更新代码
```bash
cd /var/www/electric-miniprogram/backend
git pull origin main
source .venv/bin/activate
uv sync --frozen
python manage.py migrate
python manage.py collectstatic --noinput
sudo supervisorctl restart electric_backend
```

### 零停机部署
使用Gunicorn的graceful reload：
```bash
kill -HUP $(cat /var/run/gunicorn.pid)
```

## 安全加固

### 防火墙配置
```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 限制数据库访问
```bash
# 编辑PostgreSQL配置
sudo nano /etc/postgresql/13/main/pg_hba.conf

# 只允许本地连接
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
```

### 定期更新
```bash
# 更新系统包
sudo apt update && sudo apt upgrade

# 更新Python包
pip list --outdated
pip install --upgrade package_name
```

## 故障排查

### 常见问题

#### 1. 502 Bad Gateway
- 检查Gunicorn是否运行
- 检查Nginx配置
- 查看错误日志

#### 2. 数据库连接失败
- 检查PostgreSQL服务状态
- 验证数据库凭据
- 检查防火墙规则

#### 3. 静态文件404
- 运行collectstatic
- 检查Nginx配置
- 验证文件权限

### 日志查看
```bash
# Gunicorn日志
tail -f /var/log/gunicorn/error.log

# Nginx日志
tail -f /var/log/nginx/error.log

# Supervisor日志
tail -f /var/log/supervisor/electric_backend.log

# Django日志
tail -f /var/www/electric-miniprogram/backend/logs/django.log
```

## 性能优化

### 数据库优化
- 配置连接池
- 创建适当索引
- 定期VACUUM

### 缓存配置
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### CDN配置
- 使用CDN加速静态文件
- 配置图片压缩
- 启用Gzip压缩

## 回滚方案

### 代码回滚
```bash
git log --oneline
git checkout <commit_hash>
sudo supervisorctl restart electric_backend
```

### 数据库回滚
```bash
python manage.py migrate app_name migration_name
```

## 联系支持

- 技术支持：support@example.com
- 紧急联系：+86 138-0013-8000
