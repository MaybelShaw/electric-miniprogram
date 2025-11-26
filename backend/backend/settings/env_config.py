"""
Environment configuration management module.

This module provides utilities for detecting the runtime environment and loading
environment-specific configurations. It supports development and production environments
with different security and performance settings.
"""

import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Load .env file if it exists
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(__file__).resolve().parents[2] / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Only set if not already in environment
                    if key and not os.getenv(key):
                        os.environ[key] = value

# Load .env file on module import
load_env_file()


class EnvironmentConfig:
    """
    Centralized environment configuration management.
    
    Provides methods to detect the current environment and load appropriate settings.
    Supports environment-aware configuration for security, debugging, and performance.
    """
    
    # Environment constants
    ENV_DEVELOPMENT = 'development'
    ENV_PRODUCTION = 'production'
    
    @staticmethod
    def get_env(key: str = None, default: str = None) -> str:
        """
        Get environment variable value or the current environment.
        
        Args:
            key: Environment variable name. If None, returns current environment.
            default: Default value if environment variable is not set.
        
        Returns:
            str: Environment variable value or current environment.
        """
        if key is None:
            return os.getenv('DJANGO_ENV', EnvironmentConfig.ENV_DEVELOPMENT)
        return os.getenv(key, default)
    
    @staticmethod
    def is_production() -> bool:
        """
        Check if running in production environment.
        
        Returns:
            bool: True if DJANGO_ENV is 'production', False otherwise.
        """
        return EnvironmentConfig.get_env() == EnvironmentConfig.ENV_PRODUCTION
    
    @staticmethod
    def is_development() -> bool:
        """
        Check if running in development environment.
        
        Returns:
            bool: True if DJANGO_ENV is 'development', False otherwise.
        """
        return EnvironmentConfig.get_env() == EnvironmentConfig.ENV_DEVELOPMENT
    
    @staticmethod
    def get_current_env() -> str:
        """
        Get the current environment name.
        
        Returns:
            str: Either 'development' or 'production'. Defaults to 'development'.
        """
        return os.getenv('DJANGO_ENV', EnvironmentConfig.ENV_DEVELOPMENT)
    
    @staticmethod
    def get_secret_key() -> str:
        """
        Get the Django SECRET_KEY.
        
        In production, SECRET_KEY must be set via environment variable.
        In development, a default insecure key is used for convenience.
        
        Returns:
            str: The SECRET_KEY value.
            
        Raises:
            ImproperlyConfigured: If in production and SECRET_KEY is not set.
        """
        if EnvironmentConfig.is_production():
            key = os.getenv('SECRET_KEY')
            if not key:
                raise ImproperlyConfigured(
                    'SECRET_KEY environment variable must be set in production'
                )
            return key
        
        # Development: use environment variable if set, otherwise use default
        return os.getenv(
            'SECRET_KEY',
            'django-insecure-dev-key-change-in-production'
        )
    
    @staticmethod
    def get_allowed_hosts() -> list:
        """
        Get the list of allowed hosts.
        
        In production, reads from ALLOWED_HOSTS environment variable (comma-separated).
        In development, allows all hosts for convenience.
        
        Returns:
            list: List of allowed host strings.
        """
        if EnvironmentConfig.is_production():
            hosts_str = os.getenv('ALLOWED_HOSTS', '')
            if not hosts_str:
                raise ImproperlyConfigured(
                    'ALLOWED_HOSTS environment variable must be set in production'
                )
            return [h.strip() for h in hosts_str.split(',') if h.strip()]
        
        # Development: allow all
        return ['*']
    
    @staticmethod
    def get_cors_allowed_origins() -> list:
        """
        Get the list of CORS allowed origins.
        
        In production, reads from CORS_ALLOWED_ORIGINS environment variable (comma-separated).
        In development, allows common local development origins.
        
        Returns:
            list: List of allowed origin URLs.
        """
        if EnvironmentConfig.is_production():
            origins_str = os.getenv('CORS_ALLOWED_ORIGINS', '')
            if not origins_str:
                raise ImproperlyConfigured(
                    'CORS_ALLOWED_ORIGINS environment variable must be set in production'
                )
            return [o.strip() for o in origins_str.split(',') if o.strip()]
        
        # Development: allow common local development origins
        return [
            'http://localhost:3000',
            'http://localhost:8000',
            'http://localhost:8080',
            'http://localhost:8081',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:8000',
            'http://127.0.0.1:8080',
            'http://127.0.0.1:8081',
        ]
    
    @staticmethod
    def get_debug() -> bool:
        """
        Get the DEBUG setting.
        
        In production, DEBUG is always False for security.
        In development, DEBUG is True by default for convenience.
        
        Returns:
            bool: True if debugging should be enabled, False otherwise.
        """
        if EnvironmentConfig.is_production():
            return False
        
        # Development: enable debug by default
        debug_str = os.getenv('DEBUG', 'True')
        return debug_str.lower() in ('true', '1', 'yes')
    
    @staticmethod
    def get_database_config() -> dict:
        """
        Get the database configuration.
        
        In production, uses PostgreSQL with credentials from environment variables.
        In development, uses SQLite for simplicity.
        
        Returns:
            dict: Database configuration dictionary for Django DATABASES setting.
        """
        if EnvironmentConfig.is_production():
            return {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.getenv('POSTGRES_DB', ''),
                'USER': os.getenv('POSTGRES_USER', ''),
                'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
                'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
                'PORT': os.getenv('POSTGRES_PORT', '5432'),
            }
        
        # Development: use SQLite
        from pathlib import Path
        base_dir = Path(__file__).resolve().parents[2]
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': base_dir / 'db.sqlite3',
        }
    
    @staticmethod
    def validate_production_config():
        """
        Validate that all required production environment variables are set.
        
        This should be called during application startup in production.
        
        Raises:
            ImproperlyConfigured: If any required production setting is missing.
        """
        if not EnvironmentConfig.is_production():
            return
        
        required_vars = [
            'SECRET_KEY',
            'ALLOWED_HOSTS',
            'CORS_ALLOWED_ORIGINS',
            'POSTGRES_DB',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD',
            'POSTGRES_HOST',
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ImproperlyConfigured(
                f'Missing required environment variables in production: {", ".join(missing_vars)}'
            )
