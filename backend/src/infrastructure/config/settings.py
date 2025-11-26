"""
Application Settings
Configuration management using Pydantic Settings
"""

from typing import Optional, List, Dict, Any, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
import os
import json
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="Construction Analysis Agent", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # API Keys - OpenRouter as primary LLM provider
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL")
    openrouter_app_url: Optional[str] = Field(default=None, env="OPENROUTER_APP_URL")
    openrouter_app_title: Optional[str] = Field(default=None, env="OPENROUTER_APP_TITLE")
    langsmith_api_key: Optional[str] = Field(default=None, env="LANGSMITH_API_KEY")
    
    # Database
    database_url: str = Field(
        default="postgresql://user:pass@localhost/construction_db",
        env="DATABASE_URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL"
    )
    
    # LangChain Configuration
    langchain_verbose: bool = Field(default=True, env="LANGCHAIN_VERBOSE")
    langchain_tracing: bool = Field(default=False, env="LANGCHAIN_TRACING_V2")
    langchain_project: str = Field(default="construction-agent", env="LANGCHAIN_PROJECT")
    
    # Model Configuration
    chat_model: str = Field(default="x-ai/grok-4-fast", env="CHAT_MODEL")
    vision_model: str = Field(default="google/gemini-2.5-flash-image-preview", env="VISION_MODEL")
    temperature: float = Field(default=0.3, env="MODEL_TEMPERATURE")
    max_tokens: int = Field(default=4096, env="MAX_TOKENS")
    
    # Agent Configuration
    agent_timeout: int = Field(default=120, env="AGENT_TIMEOUT")  # seconds
    max_iterations: int = Field(default=10, env="MAX_ITERATIONS")
    enable_memory: bool = Field(default=True, env="ENABLE_MEMORY")
    
    # File Storage
    upload_dir: Path = Field(default=Path("uploads"), env="UPLOAD_DIR")
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_image_extensions: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".bmp"],
        env="ALLOWED_IMAGE_EXTENSIONS"
    )
    allowed_document_extensions: List[str] = Field(
        default=[".pdf", ".docx", ".xlsx", ".txt"],
        env="ALLOWED_DOCUMENT_EXTENSIONS"
    )

    # Cloud Storage Configuration
    storage_type: str = Field(default="s3", env="STORAGE_TYPE")  # local, s3, gcs
    storage_bucket: Optional[str] = Field(default="construction-images", env="STORAGE_BUCKET")
    storage_base_path: str = Field(default="backend/storage", env="STORAGE_BASE_PATH")
    aws_access_key_id: Optional[str] = Field(default="minioadmin", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default="minioadmin123", env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_endpoint_url: Optional[str] = Field(default="http://localhost:9000", env="AWS_ENDPOINT_URL")
    gcs_credentials_path: Optional[str] = Field(default=None, env="GCS_CREDENTIALS_PATH")
    
    # Project Configuration
    max_locations_per_project: int = Field(default=3, env="MAX_LOCATIONS")
    default_quality_threshold: int = Field(default=70, env="QUALITY_THRESHOLD")
    progress_update_interval: int = Field(default=7, env="PROGRESS_INTERVAL")  # days
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    access_token_expire_minutes: int = Field(default=30, env="TOKEN_EXPIRE")
    
    # CORS
    cors_origins: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        env="CORS_ORIGINS"
    )

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            # Try to parse as JSON
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                # If not valid JSON, treat as comma-separated string
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # Railway Deploy
    railway_static_url: Optional[str] = Field(default=None, env="RAILWAY_STATIC_URL")
    port: int = Field(default=8000, env="PORT")
    
    @validator("upload_dir", pre=True)
    def create_upload_dir(cls, v):
        """Ensure upload directory exists"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @validator("openrouter_api_key")
    def validate_openrouter_key(cls, v):
        """Validate OpenRouter API key"""
        if not v or v == "":
            raise ValueError("OpenRouter API key is required")
        if not v.startswith("sk-or-"):
            raise ValueError("Invalid OpenRouter API key format (should start with sk-or-)")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    @property
    def langchain_config(self) -> Dict[str, Any]:
        """Get LangChain configuration"""
        config = {
            "verbose": self.langchain_verbose,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "model_name": self.chat_model,
            "openai_api_base": self.openrouter_base_url,
            "openai_api_key": self.openrouter_api_key
        }

        if self.langchain_tracing and self.langsmith_api_key:
            config["callbacks"] = []
            config["tracing"] = True
            config["project"] = self.langchain_project

        return config

    @property
    def llm_api_key(self) -> str:
        """Get the OpenRouter API key"""
        return self.openrouter_api_key

    @property
    def llm_base_url(self) -> str:
        """Get the OpenRouter base URL"""
        return self.openrouter_base_url
    
    @property
    def langgraph_config(self) -> Dict[str, Any]:
        """Get LangGraph configuration"""
        return {
            "recursion_limit": self.max_iterations,
            "enable_checkpointing": self.enable_memory,
            "debug": self.debug
        }
    
    @property
    def agent_config(self) -> Dict[str, Any]:
        """Get agent configuration"""
        return {
            "visual_config": {
                "model": self.vision_model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            },
            "document_config": {
                "model": self.chat_model,
                "temperature": 0.2,  # Lower for document processing
                "max_tokens": self.max_tokens,
                "chunk_size": 2000,
                "chunk_overlap": 200
            },
            "progress_config": {
                "model": self.chat_model,
                "temperature": 0.2,
                "max_tokens": 2048
            },
            "report_config": {
                "model": self.chat_model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "template_path": "templates/",
                "output_path": "reports/"
            }
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            "url": self.database_url,
            "echo": self.debug,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 1800
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        return {
            "url": self.redis_url,
            "decode_responses": True,
            "max_connections": 50
        }

    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration for StorageService"""
        config = {
            "type": self.storage_type,
            "base_path": self.storage_base_path
        }

        if self.storage_type == "s3":
            config.update({
                "bucket": self.storage_bucket,
                "aws_access_key_id": self.aws_access_key_id,
                "aws_secret_access_key": self.aws_secret_access_key,
                "region": self.aws_region,
                "endpoint_url": self.aws_endpoint_url
            })
        elif self.storage_type == "gcs":
            config.update({
                "bucket": self.storage_bucket,
                "credentials_path": self.gcs_credentials_path
            })

        return config


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
