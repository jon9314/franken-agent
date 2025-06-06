import sys
import os # Added for constructing paths, especially for Alembic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from alembic.config import Config as AlembicConfig # For running migrations
from alembic import command as alembic_command    # For running migrations

from app.api.router import api_router # Main API router
from app.core.config import settings  # Application settings
from app.db.database import Base, engine # SQLAlchemy Base and engine (not directly used for create_all if Alembic is primary)
from app.db.database import SessionLocal # For initial user creation
from app.db import crud                # For initial user creation
# Ensure models are imported if there's any fallback to Base.metadata.create_all
# from app.db import models
from app.services.plugin_manager import PluginManager # Import the PluginManager class
from app.services import plugin_manager as plugin_manager_module # To set the global instance

# --- Application Initialization ---
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json", # URL for the OpenAPI schema
    description="Frankie AI Web Agent with Self-Optimization and Genealogy Research Capabilities."
)

# --- CORS (Cross-Origin Resource Sharing) Middleware ---
# Configures which origins are allowed to make requests to the backend.
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip('/') for origin in settings.BACKEND_CORS_ORIGINS], # Ensure no trailing slashes
        allow_credentials=True, # Allow cookies to be included in requests
        allow_methods=["*"],    # Allow all standard HTTP methods
        allow_headers=["*"],    # Allow all headers
    )

# --- Logging Configuration using Loguru ---
logger.remove() # Remove default FastAPI/Uvicorn handler to replace with Loguru
# Console logger with colorization and detailed format
logger.add(
    sys.stdout, 
    colorize=True, 
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO" # Default console logging level
)
# File logger for persistent logs
# Ensure the 'data' directory exists or is created by Docker volume mapping.
log_file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "app.log"))
# Create 'data' directory if it doesn't exist (useful for local dev without Docker initially)
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logger.add(
    log_file_path, 
    rotation="10 MB",    # Rotate log file when it reaches 10MB
    retention="10 days", # Keep logs for 10 days
    level="INFO",        # File logging level
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}" # Simpler format for file
)

# --- Application Startup Events ---
@app.on_event("startup")
def on_startup():
    """
    Event handler triggered when the FastAPI application starts.
    - Applies database migrations using Alembic.
    - Creates initial user accounts from the configuration.
    - Initializes the PluginManager to load all agent plugins.
    """
    logger.info(f"Starting up {settings.APP_NAME}...")
    
    # 1. Apply Alembic database migrations
    try:
        logger.info("Attempting to apply database migrations...")
        # Construct the path to alembic.ini relative to this main.py file.
        # Assumes: main.py is in `backend/app/`, alembic.ini is in `backend/`.
        alembic_ini_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        alembic_scripts_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "alembic"))

        if not os.path.exists(alembic_ini_path):
            logger.error(f"Alembic configuration file not found at: {alembic_ini_path}. Skipping migrations.")
        else:
            alembic_cfg = AlembicConfig(alembic_ini_path)
            # Ensure alembic knows where its scripts are, relative to its own config or an absolute path
            alembic_cfg.set_main_option("script_location", alembic_scripts_path)
            # Crucially, ensure Alembic uses the DATABASE_URL from our application settings
            alembic_cfg.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))
            
            alembic_command.upgrade(alembic_cfg, "head") # Upgrade to the latest migration
            logger.info("Database migrations applied successfully (or already up to date).")
    except Exception as e:
        logger.error(f"Failed to apply database migrations: {e}", exc_info=True)
        logger.warning("Continuing startup. If this is the first run or models changed, the database might be inconsistent or tables might be missing. Manual migration might be needed.")
        # As a last resort for development or if migrations are problematic:
        # from app.db import models # Ensure models are imported
        # Base.metadata.create_all(bind=engine)
        # logger.info("Fallback: Base.metadata.create_all() called. This is not suitable for production schema changes.")

    # 2. Create initial users (if defined in config and not existing)
    try:
        db = SessionLocal()
        logger.info("Checking for and creating initial users if necessary...")
        for user_data in settings.INITIAL_USERS:
            existing_user = crud.get_user_by_email(db, email=user_data.email)
            if not existing_user:
                crud.create_user(db, user=user_data)
                logger.info(f"Created initial user: {user_data.email} with role {user_data.role}")
            else:
                logger.info(f"Initial user {user_data.email} already exists. Skipping creation.")
        db.close()
    except Exception as e:
        logger.error(f"Failed to create initial users: {e}", exc_info=True)

    # 3. Initialize Plugin Manager (discovers and loads plugins)
    try:
        logger.info("Initializing Plugin Manager...")
        # Set the global instance in the plugin_manager module
        plugin_manager_module.plugin_manager_instance = PluginManager()
        loaded_plugins_count = len(plugin_manager_module.plugin_manager_instance.list_plugins())
        logger.info(f"Plugin Manager initialized successfully. Loaded {loaded_plugins_count} plugins.")
    except Exception as e:
        logger.error(f"Failed to initialize PluginManager: {e}", exc_info=True)
        # Depending on severity, you might want to sys.exit(1) if plugins are critical for app operation.
    
    logger.info(f"'{settings.APP_NAME}' startup sequence complete. Application is ready.")


# --- API Router Inclusion ---
# Includes all routers from app/api/router.py under the /api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)


# --- Root Endpoint ---
@app.get("/", tags=["Root"], summary="Root Endpoint")
async def read_root():
    """
    Provides a welcome message indicating the application is running.
    """
    return {"message": f"Welcome to {settings.APP_NAME}! API is live."}