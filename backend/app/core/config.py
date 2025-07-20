import os
import secrets
import yaml
from pydantic import BaseModel, EmailStr, AnyHttpUrl, Field
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any

class OllamaServer(BaseModel):
    name: str
    url: AnyHttpUrl
    api_key: Optional[str] = None

class InitialUser(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: str = "user"

class NotificationEvents(BaseModel):
    awaits_review: bool = True
    error: bool = True
    applied: bool = True

class NotificationSettingsModel(BaseModel): # Renamed to avoid Pydantic v1/v2 BaseSettings conflict
    enabled: bool = False
    recipient_email: Optional[EmailStr] = Field(None, example="admin-notifications@example.com")
    notify_on: NotificationEvents = NotificationEvents()

def _default_secret() -> str:
    """Generate a default secret key if one isn't provided via environment."""
    return os.getenv("SECRET_KEY", secrets.token_urlsafe(32))


class AppSettings(BaseSettings):
    APP_NAME: str = "Frankie AI Web Agent"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default_factory=_default_secret)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    CODEBASE_PATH: str = "/frankie_codebase/"
    BASE_APP_URL: AnyHttpUrl = "http://localhost"

    # Settings typically from config.yml (can be overridden by env vars if names match)
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    DATABASE_URL: str = "sqlite:///./data/frankie.db"
    OLLAMA_SERVERS: List[OllamaServer] = [OllamaServer(name="local", url="http://host.docker.internal:11434")]
    INITIAL_USERS: List[InitialUser] = []
    notifications: NotificationSettingsModel = NotificationSettingsModel() # Nested model for notification settings

    # SMTP credentials directly from .env (prefixed or unprefixed as per your .env file)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None # Field(None, env='SMTP_PASS') if env var name differs
    SMTP_SENDER_NAME: str = "Frankie AI Agent"
    
    # Genealogy API Key Settings directly from .env
    FAMILYSEARCH_DEV_KEY: Optional[str] = None
    ANCESTRY_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env" # Load .env file first
        env_file_encoding = 'utf-8'
        case_sensitive = False # Environment variable names are case-insensitive by default on some OS
        # For Pydantic v2, use extra = 'ignore' or 'allow'
        # For Pydantic v1, extra fields in .env that are not in AppSettings are ignored.

# Helper to load and merge YAML configuration
def load_and_merge_config() -> AppSettings:
    # Default values are set by Pydantic model definitions
    # Then, values from config.yml are loaded
    # Finally, values from .env are loaded and will override YAML/defaults

    yaml_config_data = {}
    try:
        with open("config/config.yml", 'r') as f: # Path relative to project root
            yaml_file_content = yaml.safe_load(f)
            if yaml_file_content and 'app' in yaml_file_content:
                yaml_config_data = yaml_file_content['app']
    except FileNotFoundError:
        print("INFO: config/config.yml not found. Using defaults and environment variables.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing config/config.yml: {e}")
    
    # Handle nested Pydantic models specifically if they come from YAML
    if 'notifications' in yaml_config_data and isinstance(yaml_config_data['notifications'], dict):
        yaml_config_data['notifications'] = NotificationSettingsModel(**yaml_config_data['notifications'])
    if 'ollama_servers' in yaml_config_data:  # Ensure list of dicts becomes list of Pydantic models
        yaml_config_data['OLLAMA_SERVERS'] = [OllamaServer(**s) for s in yaml_config_data['ollama_servers']]
    if 'initial_users' in yaml_config_data:
        yaml_config_data['INITIAL_USERS'] = [InitialUser(**u) for u in yaml_config_data['initial_users']]
    if 'codebase_path' in yaml_config_data:
        yaml_config_data['CODEBASE_PATH'] = yaml_config_data['codebase_path']
    if 'base_app_url' in yaml_config_data:
        yaml_config_data['BASE_APP_URL'] = yaml_config_data['base_app_url']

    # Create AppSettings instance.
    # Pydantic-settings will:
    # 1. Use defaults from AppSettings model.
    # 2. Override with values from `yaml_config_data` if provided as kwargs.
    # 3. Override with values from `.env` file (due to `env_file` in Config).
    # 4. Override with actual environment variables.
    # The order of precedence for pydantic-settings is generally:
    # init_kwargs > env_vars > dotenv_vars > model_defaults > yaml_loaded_defaults (if passed to init)
    # To achieve YAML -> .env -> env_vars, we load YAML first, then let BaseSettings handle .env and actual env vars.
    
    return AppSettings(**yaml_config_data)

settings = load_and_merge_config()

# Log loaded settings (optional, for debugging)
# from loguru import logger
# logger.info(f"Loaded settings: {settings.model_dump_json(indent=2)}")
