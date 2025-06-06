from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError # For validating token data schema
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM # SECRET_KEY is in settings
from app.db import crud, models, schemas # schemas needed for TokenData
from app.db.database import SessionLocal # To create DB sessions

# OAuth2PasswordBearer scheme for token handling.
# tokenUrl points to the API endpoint where clients get the token (login endpoint).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

def get_db():
    """
    FastAPI dependency that provides a database session for a request.
    Ensures the session is properly closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> models.User:
    """
    FastAPI dependency to get the current user from a JWT token.
    Validates the token, decodes it, and fetches the user from the database.
    Raises HTTPException if the token is invalid or the user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}, # Standard header for Bearer token auth
    )
    try:
        payload = jwt.decode(
            token, 
            str(settings.SECRET_KEY), # Ensure SECRET_KEY is string
            algorithms=[ALGORITHM]
        )
        email: Optional[str] = payload.get("sub") # 'sub' (subject) usually holds the username/email
        if email is None:
            raise credentials_exception
        # Optionally, validate token structure further using a Pydantic model if needed
        token_data = schemas.TokenData(email=email)
    except JWTError: # Covers various issues like expired signature, invalid signature etc.
        raise credentials_exception
    except ValidationError: # If token_data schema validation fails (e.g. email format)
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user( # pylint: disable=unused-argument
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    FastAPI dependency to get the current active user.
    This can be extended to check an `is_active` flag on the User model.
    For now, it assumes any user retrieved by get_current_user is active.
    """
    # Example: If you add an `is_active` boolean field to your User model:
    # if not current_user.is_active:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def get_current_admin_user(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    FastAPI dependency to ensure the current user has the 'admin' role.
    Raises HTTPException if the user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, # Correct status code for authorization failure
            detail="The user doesn't have enough privileges for this resource.",
        )
    return current_user