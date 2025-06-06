from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, get_current_active_user
from app.db import schemas, crud, models
from app.services.ollama_service import ollama_service # Import the global service instance

router = APIRouter()

@router.post("/", response_model=schemas.ChatResponse, status_code=status.HTTP_200_OK)
async def handle_chat_interaction( # Renamed for clarity
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    chat_request: schemas.ChatRequest, # Request body with prompt and optional model
):
    """
    Receive a user's prompt, get a response from the configured Ollama model
    (or a specific model if provided in the request), and save the interaction
    to the user's chat history.
    """
    if not chat_request.prompt or not chat_request.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Prompt cannot be empty."
        )

    # Call the Ollama service to get a response
    # The service handles selecting the model and server.
    ollama_result = await ollama_service.generate(
        prompt=chat_request.prompt, model_name=chat_request.model
    )

    if "error" in ollama_result: # Check if the Ollama service returned an error
        # Log the detailed error for backend diagnosis
        logger.error(f"Ollama service error for user {current_user.email}: {ollama_result.get('error')} - Raw: {ollama_result.get('_raw_error_content', '')}")
        # Return a generic error to the client
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=f"AI service unavailable or encountered an error: {ollama_result['error']}"
        )

    # Save the successful interaction to chat history
    crud.create_chat_history_entry(
        db=db,
        user_id=current_user.id,
        entry=chat_request, # Pass the original request for prompt
        response_text=ollama_result["response"], # The actual text response from LLM
        model_used=ollama_result["model_used"]
    )

    return schemas.ChatResponse(
        response=ollama_result["response"], 
        model_used=ollama_result["model_used"]
    )


@router.get("/history", response_model=List[schemas.ChatHistoryEntry])
def get_user_chat_history_list( # Renamed for clarity
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 50 # Default limit for history entries
):
    """
    Retrieve the current authenticated user's chat history, paginated.
    Ordered by most recent first.
    """
    history_entries = crud.get_user_chat_history(db, user_id=current_user.id, skip=skip, limit=limit)
    return history_entries