from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.core.dependencies import get_current_active_user # For authentication
from app.db import schemas, models # User model for dependency, schemas for response
from app.services.ollama_service import ollama_service # Global service instance

router = APIRouter()

@router.get("/", response_model=List[schemas.ModelInfo])
async def list_available_ollama_models_endpoint( # Renamed for clarity
    *,
    # This endpoint could be open or restricted.
    # Requiring authentication ensures only logged-in users can see the model list.
    current_user: models.User = Depends(get_current_active_user) 
):
    """
    Get a list of all available models from all configured Ollama servers.
    The response includes the server name (nickname from config) and the model name.
    """
    try:
        models_list = await ollama_service.list_models()
        if models_list is None: # Should not happen if service is robust
            raise HTTPException(status_code=503, detail="Could not retrieve model list from AI service.")
        return models_list
    except Exception as e:
        logger.error(f"Error listing Ollama models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching AI models.")