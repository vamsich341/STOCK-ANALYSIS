"""
Configuration file for Stock Analysis Application
"""

import os
from urllib.parse import urlparse

class Config:
    """Application configuration"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    PORT = int(os.environ.get('PORT', 8000))
    
    # Database configuration (Lakebase Postgres)
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'postgresql://ROOTUSER:npg_fsCrk8DWK3nj@ep-falling-thunder-d8fyunjf.database.us-east-2.cloud.databricks.com/databricks_postgres?sslmode=require'
    )
    
    # Parse database URL
    db_url = urlparse(DATABASE_URL)
    DB_HOST = db_url.hostname
    DB_PORT = db_url.port or 5432
    DB_NAME = db_url.path.lstrip('/')
    DB_USER = db_url.username
    DB_PASSWORD = db_url.password
    
    # Massive API configuration
    MASSIVE_API_KEY = os.environ.get('MASSIVE_API_KEY', '0JTHKK3cpM_Zv4lOFt9xpxaGtC6DtQlv')
    MASSIVE_API_BASE_URL = 'https://api.massive.io/v1'
    
    # Analysis configuration
    MAX_HISTORICAL_DAYS = 365
    DEFAULT_NEWS_LIMIT = 10
    CACHE_TTL = 300  # 5 minutes cache for API responses
    
    # Embedding configuration (for semantic search)
    EMBEDDING_MODEL = 'text-embedding-ada-002'
    EMBEDDING_DIMENSION = 1536
    
    # Rate limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_PER_MINUTE = 60
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')