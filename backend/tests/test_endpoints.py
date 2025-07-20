import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from typing import Generator # For type hinting the fixture

from app.main import app  # Import the FastAPI application instance
from app.core.config import settings  # Application settings
from app.db.database import Base
from app.core.dependencies import get_db

# Setup a separate test database specifically for these endpoint tests
SQLALCHEMY_DATABASE_URL_ENDPOINTS = "sqlite:///./test_endpoints_db.db" # Unique name
engine_endpoints = create_engine(
    SQLALCHEMY_DATABASE_URL_ENDPOINTS, connect_args={"check_same_thread": False}
)
TestingSessionLocalEndpoints = sessionmaker(autocommit=False, autoflush=False, bind=engine_endpoints)

# Override the get_db dependency for the scope of these tests
def override_get_db_for_endpoints() -> Generator[SQLAlchemySession, None, None]:
    try:
        db = TestingSessionLocalEndpoints()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function", autouse=True) # autouse ensures it runs for every test in this file
def setup_and_teardown_db_endpoints():
    Base.metadata.create_all(bind=engine_endpoints) # Create tables for this test session
    original_get_db = app.dependency_overrides.get(get_db) # Store original override if any
    app.dependency_overrides[get_db] = override_get_db_for_endpoints # Apply override
    yield
    Base.metadata.drop_all(bind=engine_endpoints) # Drop tables after tests
    if original_get_db: # Restore original override
        app.dependency_overrides[get_db] = original_get_db
    else:
        del app.dependency_overrides[get_db] # Remove override if none was there

# Create a TestClient instance using the FastAPI app
client = TestClient(app)

def test_read_root_endpoint():
    """Tests the main root endpoint ("/") of the application."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome to {settings.APP_NAME}! API is live."}

def test_non_existent_api_route():
    """Tests that accessing a non-existent API route returns a 404 Not Found error."""
    response = client.get(f"{settings.API_V1_STR}/this-route-does-not-exist-at-all-123")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

def test_openapi_json_accessible():
    """Tests if the OpenAPI (Swagger) JSON schema is accessible."""
    response = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    json_response = response.json()
    assert json_response["info"]["title"] == settings.APP_NAME
