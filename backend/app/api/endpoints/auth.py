from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any

from app.core import security # For password hashing and token creation
from app.core.dependencies import get_db, get_current_active_user # FastAPI dependencies
from app.db import crud, schemas, models # Database models and Pydantic schemas

router = APIRouter()

@router.post("/register", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED)
def register_new_user( # Renamed for clarity
    *,
    db: Session = Depends(get_db),
    user_in: schemas.UserCreate, # Pydantic model for request body
) -> Any:
    """
    Create a new user in the system.
    - Email must be unique.
    - Password will be hashed before storage.
    - Default role is 'user'.
    """
    existing_user = crud.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )
    new_user = crud.create_user(db, user=user_in)
    return new_user


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends() # Standard form data for OAuth2
) -> Any:
    """
    OAuth2 compatible token login.
    Takes username (email) and password from form data, returns an access token.
    """
    user = crud.get_user_by_email(db, email=form_data.username) # form_data.username is the email
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"}, # Standard for Bearer token auth
        )
    
    # Data to be encoded in the JWT
    access_token_data = {"sub": user.email} # 'sub' (subject) is standard for user identifier
    access_token = security.create_access_token(data=access_token_data)
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserPublic)
def read_authenticated_user_me( # Renamed for clarity
    current_user: models.User = Depends(get_current_active_user), # Dependency injects authenticated user
) -> Any:
    """
    Get details for the currently authenticated user.
    """
    return current_user