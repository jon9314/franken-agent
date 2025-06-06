from datetime import datetime, timedelta, timezone # Ensure timezone is imported
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings # To get SECRET_KEY and TOKEN_EXPIRE_MINUTES

# Password Hashing Context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Algorithm
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a plain password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    The 'data' dictionary is encoded into the token.
    'sub' (subject) key in data is typically the user's identifier (e.g., email).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    # Ensure SECRET_KEY is a string
    encoded_jwt = jwt.encode(to_encode, str(settings.SECRET_KEY), algorithm=ALGORITHM)
    return encoded_jwt