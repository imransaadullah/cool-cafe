from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CyberCafe Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/cybercafe"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DASHBOARD_PORT: int = 7842
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:7842", "http://localhost:8080"]
    
    # Sync
    SYNC_ENABLED: bool = True
    SYNC_INTERVAL_MINUTES: int = 30
    GLOBAL_SERVER_URL: Optional[str] = None
    
    # Deployment mode: local_only, hybrid, global_only
    DEPLOYMENT_MODE: str = "local_only"
    
    # Branch
    BRANCH_ID: Optional[int] = None
    
    # Filtering
    DNS_BLOCKING: bool = True
    PROCESS_BLOCKING: bool = False
    URL_FILTERING: bool = False
    
    # Payment
    PAYSTACK_SECRET_KEY: Optional[str] = None
    PAYSTACK_PUBLIC_KEY: Optional[str] = None
    KONGA_PAY_MERCHANT_ID: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
