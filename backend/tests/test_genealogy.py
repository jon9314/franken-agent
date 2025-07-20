import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from typing import Generator, Dict, Any  # For type hinting
import os  # For file path construction
import tempfile

from app.main import app
from app.core.dependencies import get_db
from app.db.database import Base
from app.db import models, schemas, crud # Ensure all are imported
from app.core.config import settings

# Use a separate test database for genealogy tests to ensure isolation
SQLALCHEMY_DATABASE_URL_GENEALOGY = "sqlite:///./test_genealogy_module_db.db" # Unique name
engine_genealogy = create_engine(
    SQLALCHEMY_DATABASE_URL_GENEALOGY, connect_args={"check_same_thread": False}
)
TestingSessionLocalGenealogy = sessionmaker(autocommit=False, autoflush=False, bind=engine_genealogy)

def override_get_db_for_genealogy() -> Generator[SQLAlchemySession, None, None]:
    try:
        db = TestingSessionLocalGenealogy()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function") # Fixture runs once per test function
def test_db_genealogy_session_setup(): # Renamed to avoid conflict if imported elsewhere
    Base.metadata.create_all(bind=engine_genealogy) # Create tables
    original_get_db = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db_for_genealogy # Apply override
    
    db_session = TestingSessionLocalGenealogy() # Create a session for setup/teardown data
    try:
        yield db_session # Provide the session to the fixture user (the test function)
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine_genealogy) # Drop tables after tests
        if original_get_db: # Restore original override
            app.dependency_overrides[get_db] = original_get_db
        else:
            if get_db in app.dependency_overrides: # Check if key exists before deleting
                 del app.dependency_overrides[get_db]

client = TestClient(app) # Client will use the overridden DB via app context

@pytest.fixture
def admin_user_headers_genealogy(test_db_genealogy_session_setup: SQLAlchemySession) -> Dict[str, str]:
    """Fixture to create an admin user and return authentication headers."""
    user_email = "genealogy_admin@example.com"
    user_password = "securepassword123"
    
    # Use the session provided by the fixture to interact with the test DB
    existing_user = crud.get_user_by_email(test_db_genealogy_session_setup, email=user_email)
    if not existing_user:
        crud.create_user(test_db_genealogy_session_setup, user=schemas.UserCreate(
            email=user_email, password=user_password, full_name="Genealogy Admin User", role="admin"
        ))

    # Log in to get a token
    response = client.post(
        f"{settings.API_V1_STR}/auth/token", 
        data={"username": user_email, "password": user_password}
    )
    assert response.status_code == 200, f"Admin login failed for genealogy tests: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# Construct path to sample.ged relative to this test file's location or project root
# Assuming tests are run from project root (frankie/) or backend/
SAMPLE_GEDCOM_PATH = os.path.join(os.path.dirname(__file__), "assets", "sample.ged")
if not os.path.exists(SAMPLE_GEDCOM_PATH): # Fallback if tests run from backend/ dir
    SAMPLE_GEDCOM_PATH = os.path.join("tests", "assets", "sample.ged")


def test_upload_valid_gedcom_file(admin_user_headers_genealogy: Dict[str, str], test_db_genealogy_session_setup: SQLAlchemySession):
    """Test uploading a valid GEDCOM file."""
    assert os.path.exists(SAMPLE_GEDCOM_PATH), f"Sample GEDCOM file not found at {SAMPLE_GEDCOM_PATH}"
    
    with open(SAMPLE_GEDCOM_PATH, "rb") as f:
        response = client.post(
            f"{settings.API_V1_STR}/genealogy/trees/upload",
            files={"file": ("sample.ged", f, "application/gcom")}, # Common MIME type for .ged
            headers=admin_user_headers_genealogy
        )
    assert response.status_code == 201, f"GEDCOM Upload failed: {response.text}"
    data = response.json()
    assert data["file_name"] == "sample.ged"
    assert "id" in data
    
    # Verify data persistence in the database using the test session
    tree_in_db = test_db_genealogy_session_setup.query(models.FamilyTree).filter(models.FamilyTree.id == data["id"]).first()
    assert tree_in_db is not None
    assert tree_in_db.file_name == "sample.ged"
    # Further checks on persons/families count can be added if GenealogyService is robust
    persons_count = test_db_genealogy_session_setup.query(models.Person).filter(models.Person.tree_id == tree_in_db.id).count()
    assert persons_count == 3 # Based on sample.ged

def test_upload_invalid_file_type(admin_user_headers_genealogy: Dict[str, str]):
    """Test uploading a file that is not a .ged file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=True) as tmp_file:
        tmp_file.write("This is not a gedcom file.")
        tmp_file.flush() # Ensure content is written
        with open(tmp_file.name, "rb") as f:
            response = client.post(
                f"{settings.API_V1_STR}/genealogy/trees/upload",
                files={"file": ("invalid.txt", f, "text/plain")},
                headers=admin_user_headers_genealogy
            )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

def test_get_user_family_trees_list(admin_user_headers_genealogy: Dict[str, str], test_db_genealogy_session_setup: SQLAlchemySession):
    """Test listing uploaded family trees for the authenticated user."""
    # Ensure at least one tree is uploaded by this user
    with open(SAMPLE_GEDCOM_PATH, "rb") as f:
        client.post(f"{settings.API_V1_STR}/genealogy/trees/upload", files={"file": ("sample_for_list.ged", f)}, headers=admin_user_headers_genealogy)

    response = client.get(f"{settings.API_V1_STR}/genealogy/trees", headers=admin_user_headers_genealogy)
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1 # Should have at least the one we uploaded
    assert any(tree['file_name'] == "sample_for_list.ged" for tree in data)

def test_get_family_tree_details(admin_user_headers_genealogy: Dict[str, str], test_db_genealogy_session_setup: SQLAlchemySession):
    """Test getting the details of a specific tree, verifying parsed content."""
    upload_resp = None
    with open(SAMPLE_GEDCOM_PATH, "rb") as f: # Use the correct path
        upload_resp = client.post(f"{settings.API_V1_STR}/genealogy/trees/upload", files={"file": ("sample_detail.ged", f)}, headers=admin_user_headers_genealogy)
    assert upload_resp.status_code == 201
    tree_id = upload_resp.json()["id"]

    response = client.get(f"{settings.API_V1_STR}/genealogy/trees/{tree_id}", headers=admin_user_headers_genealogy)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == tree_id
    assert data["file_name"] == "sample_detail.ged"
    assert len(data["persons"]) == 3 # From sample.ged
    assert len(data["families"]) == 1 # From sample.ged

    # Verify some specific parsed data more robustly
    john_smith = next((p for p in data["persons"] if p["gedcom_id"] == "@I1@"), None)
    assert john_smith is not None
    assert john_smith["first_name"] == "John"
    assert john_smith["last_name"] == "Smith"
    assert john_smith["birth_date"] == "1 JAN 1900"
    assert john_smith["birth_place"] == "New York City, New York, USA"
