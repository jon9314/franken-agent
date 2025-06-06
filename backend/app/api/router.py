from fastapi import APIRouter

from .endpoints import auth
from .endpoints import chat
from .endpoints import models as ollama_models_router # Alias to avoid name collision
from .endpoints import admin
from .endpoints import genealogy

api_router = APIRouter()

# Include authentication routes (e.g., /auth/token, /auth/register)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Include basic chat routes (e.g., /chat/, /chat/history)
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])

# Include Ollama model listing routes (e.g., /models/)
api_router.include_router(ollama_models_router.router, prefix="/models", tags=["LLM Models"])

# Include all administrative routes (e.g., /admin/users, /admin/agent/tasks)
api_router.include_router(admin.router, prefix="/admin", tags=["Admin & Agent Management"])

# Include genealogy routes (e.g., /genealogy/trees/upload, /genealogy/findings/{id}/accept)
api_router.include_router(genealogy.router, prefix="/genealogy", tags=["Genealogy"])