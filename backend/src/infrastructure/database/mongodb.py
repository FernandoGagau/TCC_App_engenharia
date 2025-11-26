"""
MongoDB Database Configuration
Using Motor (async MongoDB driver) and Beanie ODM
"""

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from typing import Optional
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""

    # MongoDB connection settings - MUST be provided via environment variables
    # Accepts both MONGODB_URL and DB_MONGODB_URL
    mongodb_url: str  # No default value - must come from environment
    database_name: str = "construction_agent"

    # Connection pool settings
    max_pool_size: int = 10
    min_pool_size: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **data):
        # Try MONGODB_URL first, then DB_MONGODB_URL
        if 'mongodb_url' not in data:
            mongodb_url = os.getenv('MONGODB_URL') or os.getenv('DB_MONGODB_URL')
            if mongodb_url:
                data['mongodb_url'] = mongodb_url

        if 'database_name' not in data:
            database_name = os.getenv('MONGODB_DATABASE') or os.getenv('DB_DATABASE_NAME')
            if database_name:
                data['database_name'] = database_name

        super().__init__(**data)


class MongoDB:
    """MongoDB database manager"""

    client: Optional[AsyncIOMotorClient] = None
    database = None

    @classmethod
    async def connect_db(cls, settings: Optional[DatabaseSettings] = None):
        """Connect to MongoDB"""
        try:
            if settings is None:
                settings = DatabaseSettings()

            # Log MongoDB URL (masked)
            masked_url = settings.mongodb_url
            if '@' in masked_url:
                # Mask password in URL for logging
                parts = masked_url.split('@')
                user_pass = parts[0].split('://')[-1]
                if ':' in user_pass:
                    user = user_pass.split(':')[0]
                    masked_url = masked_url.replace(user_pass, f"{user}:***")

            logger.info(f"🔌 Connecting to MongoDB: {masked_url}")
            logger.info(f"📦 Database name: {settings.database_name}")

            # Create MongoDB client
            cls.client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=settings.max_pool_size,
                minPoolSize=settings.min_pool_size
            )

            # Get database
            cls.database = cls.client[settings.database_name]

            # Import all document models
            from infrastructure.database.models import (
                SessionModel,
                MessageModel,
                ProjectModel,
                ImageAnalysisModel,
                EventModel,
                FileModel
            )

            # Import token models
            from infrastructure.database.token_models import (
                TokenUsageModel,
                TokenSessionSummaryModel
            )

            # Import project models
            from infrastructure.database.project_models import (
                ConstructionProjectModel,
                ProjectImageModel,
                AnalysisReport,
                ProjectAlertModel,
                ProjectScheduleModel
            )

            # Import auth models
            try:
                from domain.auth_models_mongo import (
                    User,
                    RefreshToken,
                    LoginAttempt,
                    PasswordHistory
                )
                auth_models = [
                    User,
                    RefreshToken,
                    LoginAttempt,
                    PasswordHistory
                ]
            except ImportError:
                auth_models = []

            # Import other models if they exist
            try:
                from infrastructure.database.project_analysis_models import (
                    ProjectAnalysisModel,
                    TimelineImageModel,
                    QualityCheckModel,
                    SafetyIncidentModel
                )
                additional_models = [
                    ProjectAnalysisModel,
                    TimelineImageModel,
                    QualityCheckModel,
                    SafetyIncidentModel
                ]
            except ImportError:
                additional_models = []

            try:
                from infrastructure.database.agent_models import (
                    AgentSessionModel,
                    AgentResponseModel
                )
                agent_models = [AgentSessionModel, AgentResponseModel]
            except ImportError:
                agent_models = []

            # Build document models list
            document_models = [
                # Chat models
                SessionModel,
                MessageModel,
                ProjectModel,
                ImageAnalysisModel,
                EventModel,
                FileModel,
                # Token models
                TokenUsageModel,
                TokenSessionSummaryModel,
                # Project models
                ConstructionProjectModel,
                ProjectImageModel,
                AnalysisReport,
                ProjectAlertModel,
                ProjectScheduleModel
            ]

            # Add optional models if available
            document_models.extend(additional_models)
            document_models.extend(agent_models)
            document_models.extend(auth_models)

            # Initialize Beanie with document models
            await init_beanie(
                database=cls.database,
                document_models=document_models
            )

            # Test connection
            await cls.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB: {settings.database_name}")

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            # Try fallback to local file storage
            logger.warning("⚠️ Falling back to local JSON storage")
            raise

    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")

    @classmethod
    async def get_database(cls):
        """Get database instance"""
        if cls.database is None:
            await cls.connect_db()
        return cls.database

    @classmethod
    async def health_check(cls) -> bool:
        """Check database health"""
        try:
            if cls.client:
                await cls.client.admin.command('ping')
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
        return False


# Create global instance
mongodb = MongoDB()


async def get_database():
    """Dependency to get database instance"""
    return await mongodb.get_database()