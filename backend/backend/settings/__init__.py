"""Settings package entrypoint.

The settings are organized as follows:
- base.py: Common settings shared across all environments
- development.py: Development-specific settings (DEBUG=True, SQLite, loose CORS)
- production.py: Production-specific settings (DEBUG=False, PostgreSQL, strict security)
- env_config.py: Environment detection and configuration utilities

To use a specific settings module, set the DJANGO_SETTINGS_MODULE environment variable:
  export DJANGO_SETTINGS_MODULE=backend.settings.development  # for development
  export DJANGO_SETTINGS_MODULE=backend.settings.production   # for production

The environment is also controlled by the DJANGO_ENV variable:
  export DJANGO_ENV=development  # default
  export DJANGO_ENV=production   # for production

In production, the following environment variables must be set:
  - SECRET_KEY: Django secret key
  - ALLOWED_HOSTS: Comma-separated list of allowed hosts
  - CORS_ALLOWED_ORIGINS: Comma-separated list of allowed CORS origins
  - POSTGRES_DB: PostgreSQL database name
  - POSTGRES_USER: PostgreSQL user
  - POSTGRES_PASSWORD: PostgreSQL password
  - POSTGRES_HOST: PostgreSQL host
  - POSTGRES_PORT: PostgreSQL port (optional, defaults to 5432)
"""