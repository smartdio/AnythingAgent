from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field
import os
from dotenv import load_dotenv

# Load environment variables, override=True ensures existing environment variables are overwritten
load_dotenv(override=True)

class Settings(BaseSettings):
    """Application configuration class"""
    
    # Application configuration
    APP_NAME: str = "AnythingAgent"
    DEBUG: bool = False
    
    # API configuration
    API_V1_STR: str = "/v1"
    
    # Database configuration
    LANCEDB_URI: str = "data/lancedb"
    
    # Security configuration
    ENABLE_API_KEY: bool = False
    API_KEY_NAME: str = "Authorization"
    API_KEY_PREFIX: str = "Bearer"
    API_KEY: str = Field(..., description="API key")
    
    # Model configuration
    DEFAULT_MODEL: str = "gpt-3.5-turbo"
    MODELS_DIR: str = "models"  # Models directory, relative to project root
    
    # File configuration
    UPLOAD_DIR: str = "data/uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Vector configuration
    VECTOR_SIZE: int = 1536
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Log configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global configuration instance
settings = Settings() 