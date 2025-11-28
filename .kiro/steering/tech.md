# Technology Stack

## Backend

**Framework & Language**
- Python 3.12+
- Django 5.2+
- Django REST Framework 3.16+

**Key Libraries**
- `djangorestframework-simplejwt` - JWT authentication
- `drf-spectacular` - OpenAPI/Swagger documentation
- `django-cors-headers` - CORS support
- `Pillow` - Image processing

**Database**
- SQLite (development)
- PostgreSQL 14+ (production recommended)

**Package Management**
- `uv` - Modern Python package manager (preferred)
- `pip` - Alternative package manager

## Frontend (User Mini-Program)

**Framework**
- Taro 4.1.8 - Cross-platform mini-program framework
- React 18+
- TypeScript 5.4+

**Build Tools**
- Vite 4+
- Babel

**Styling**
- Sass 1.75+

**Supported Platforms**
- WeChat Mini-Program
- Alipay Mini-Program
- H5 Web
- ByteDance (Douyin/TikTok)
- QQ, JD, Baidu mini-programs

## Merchant Admin

**Framework**
- React 18+
- TypeScript 5.3+
- Ant Design 5.12+
- Ant Design Pro Components 2.6+

**Build & Dev Tools**
- Vite 5+
- React Router 6+

**HTTP Client**
- Axios 1.6+

## Common Development Commands

### Backend

```bash
# Setup
uv sync                          # Install dependencies
python manage.py migrate         # Run database migrations
python manage.py createsuperuser # Create admin user

# Development
python manage.py runserver       # Start dev server (port 8000)

# Database
python manage.py makemigrations  # Create migration files
python manage.py migrate         # Apply migrations

# Utilities
python manage.py shell           # Django shell
python manage.py test            # Run tests
python manage.py collectstatic   # Collect static files (production)
```

### Frontend (Mini-Program)

```bash
# Setup
npm install                      # Install dependencies

# Development
npm run dev:weapp               # WeChat mini-program
npm run dev:alipay              # Alipay mini-program
npm run dev:h5                  # H5 web app

# Build
npm run build:weapp             # Build for WeChat
npm run build:alipay            # Build for Alipay
npm run build:h5                # Build for H5
```

### Merchant Admin

```bash
# Setup
npm install                      # Install dependencies

# Development
npm run dev                      # Start dev server (port 5173)

# Build
npm run build                    # Production build
npm run preview                  # Preview production build
```

## API Documentation

- Swagger UI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`

## Environment Configuration

Backend uses environment-based settings:
- `DJANGO_ENV=development` - Development mode
- `DJANGO_ENV=production` - Production mode

Configuration files:
- `backend/backend/settings/base.py` - Base settings
- `backend/backend/settings/development.py` - Dev overrides
- `backend/backend/settings/production.py` - Production overrides
- `.env` - Environment variables (not in git)
