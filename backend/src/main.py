"""
Main FastAPI Application
Construction Engineering Analysis Agent System
Using LangChain and LangGraph Latest Versions
Following SOLID principles and DDD architecture
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn

# Add src to path
sys.path.append(str(Path(__file__).parent))

# Import application modules
from infrastructure.config.settings import Settings
from infrastructure.config.cors import get_cors_origins
from infrastructure.app_state import initialize_app_state, get_app_state
from infrastructure.database.mongodb import mongodb
from infrastructure.agents.agent_factory import AgentFactory
from infrastructure.storage_service import StorageService
from application.services.project_service import ProjectService
from application.services.chat_service import ChatService

# Import API routers
from presentation.api import project_routes
from presentation.api.v1 import chat
from presentation.api import system
from presentation.api import dashboard_routes
from presentation.api import timeline_routes

# Load environment variables from backend/.env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import auth modules - use simple self-contained auth (after logger is defined)
try:
    from presentation.api.auth_simple import router as auth_router
    auth_available = True
    logger.info("Simple auth router loaded successfully")
except Exception as e:
    logger.warning(f"Auth router not available: {e}")
    auth_available = False




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Construction Analysis Agent System...")

    try:
        # Initialize settings
        settings = Settings()

        # Initialize MongoDB - REQUIRED
        try:
            await mongodb.connect_db()
            db_connected = True
            logger.info("✅ MongoDB connected successfully")

            # Test MongoDB write operation
            try:
                test_collection = mongodb.database.get_collection("_connection_test")
                test_doc = {"test": "connection", "timestamp": datetime.utcnow().isoformat()}
                result = await test_collection.insert_one(test_doc)
                await test_collection.delete_one({"_id": result.inserted_id})
                logger.info("✅ MongoDB write test successful")
            except Exception as write_error:
                logger.error(f"❌ MongoDB write test failed: {write_error}")
                raise

        except Exception as mongo_error:
            db_connected = False
            logger.error(f"❌ MongoDB connection REQUIRED but failed: {str(mongo_error)}")
            logger.error("Please ensure MongoDB is running:")
            logger.error("  docker-compose up -d mongodb")
            logger.error("Or set DB_MONGODB_URL in .env file")
            raise RuntimeError("MongoDB connection is required to start the application") from mongo_error

        # Initialize storage service
        storage_config = settings.get_storage_config()
        storage_service = StorageService(storage_config)
        logger.info(f"✅ Storage service initialized ({storage_config['type']})")

        # Initialize agent factory with latest LangChain/LangGraph
        agent_factory = AgentFactory(settings, storage_service)
        await agent_factory.initialize()

        # Initialize services
        project_service = ProjectService(
            db=mongodb,
            settings=settings
        )

        chat_service = ChatService(
            agent_factory=agent_factory,
            project_service=project_service,
            settings=settings
        )

        # Initialize application state
        initialize_app_state(
            settings=settings,
            agent_factory=agent_factory,
            project_service=project_service,
            chat_service=chat_service,
            db_connected=db_connected
        )

        logger.info("System initialized successfully")

    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down system...")

    try:
        await mongodb.close_db()

        app_state = get_app_state()
        if app_state.agent_factory:
            await app_state.agent_factory.cleanup()

        logger.info("System shutdown complete")

    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="Construction Analysis Agent API",
    description="AI-powered construction project analysis using LangChain and LangGraph",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"📥 {request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
    response = await call_next(request)
    logger.info(f"📤 {request.method} {request.url.path} - Status: {response.status_code}")
    return response

# Mount static files if directory exists
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers - Use modern v1 chat routes with SupervisorAgent integration
app.include_router(system.router, tags=["system"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(project_routes.router, prefix="/api/projects", tags=["projects"])
app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(timeline_routes.router, prefix="/api/timeline", tags=["timeline"])

# Include auth router if available
if auth_available:
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    logger.info("Auth router registered at /api/auth")
else:
    logger.warning("Auth router not available - authentication endpoints disabled")



if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
