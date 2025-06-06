import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from unittest.mock import patch, AsyncMock, MagicMock # For mocking async functions and objects
import os
import tempfile # For creating temporary files/directories if needed for tests
import shutil # For cleaning up temp directories

from app.main import app
from app.core.dependencies import get_db
from app.db.database import Base
from app.db import models, schemas, crud
from app.core.config import settings
from app.services.plugin_manager import PluginManager # For direct instantiation if needed for complex setup
from app.services import plugin_manager as pm_module # To potentially set global instance

# Test DB for agent tests
SQLALCHEMY_DATABASE_URL_AGENT = "sqlite:///./test_agent_modifier_db.db" # Unique name
engine_agent = create_engine(
    SQLALCHEMY_DATABASE_URL_AGENT, connect_args={"check_same_thread": False}
)
TestingSessionLocalAgent = sessionmaker(autocommit=False, autoflush=False, bind=engine_agent)

def override_get_db_for_agent_tests():
    try:
        db = TestingSessionLocalAgent()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def test_db_agent_session():
    Base.metadata.create_all(bind=engine_agent)
    original_get_db = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db_for_agent_tests
    
    # Initialize a test PluginManager instance specifically for these tests
    # This is crucial if the global plugin_manager_instance isn't suitable or might be uninitialized
    # Make sure the plugin_dir points to the actual plugins for discovery
    test_plugin_manager = PluginManager(plugin_dir_name="plugins") # Assumes plugins are in app/plugins
    original_pm_instance = pm_module.plugin_manager_instance
    pm_module.plugin_manager_instance = test_plugin_manager

    db = TestingSessionLocalAgent()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_agent)
        if original_get_db:
            app.dependency_overrides[get_db] = original_get_db
        else:
            if get_db in app.dependency_overrides:
                 del app.dependency_overrides[get_db]
        pm_module.plugin_manager_instance = original_pm_instance # Restore original plugin manager

client = TestClient(app)

@pytest.fixture
def admin_headers_agent(test_db_agent_session: SQLAlchemySession):
    user_email = "code_agent_admin@example.com"
    user_password = "supersecure123"
    existing_user = crud.get_user_by_email(test_db_agent_session, email=user_email)
    if not existing_user:
        crud.create_user(test_db_agent_session, user=schemas.UserCreate(
            email=user_email, password=user_password, full_name="Code Agent Admin", role="admin"
        ))
    response = client.post(f"{settings.API_V1_STR}/auth/token", data={"username": user_email, "password": user_password})
    assert response.status_code == 200, f"Login failed: {response.text}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

@pytest.fixture
def temp_codebase():
    """Creates a temporary directory structure mimicking the project for testing file ops."""
    base_dir = tempfile.mkdtemp(prefix="frankie_test_codebase_")
    backend_app_dir = os.path.join(base_dir, "backend", "app")
    frontend_src_dir = os.path.join(base_dir, "frontend", "src")
    os.makedirs(backend_app_dir, exist_ok=True)
    os.makedirs(frontend_src_dir, exist_ok=True)
    
    # Create some dummy files
    with open(os.path.join(backend_app_dir, "sample_service.py"), "w") as f:
        f.write("def original_function():\n    return 'original_backend'")
    with open(os.path.join(frontend_src_dir, "SampleComponent.jsx"), "w") as f:
        f.write("export default function Sample() { return <div>Original Frontend</div>; }")
        
    # Initialize a Git repo in this temp codebase
    from git import Repo
    Repo.init(base_dir)
    
    yield base_dir # Provide the path to the test function
    
    shutil.rmtree(base_dir) # Cleanup

# Using multiple patch decorators correctly
@patch('app.plugins.code_modifier_plugin.ollama_service.generate_json', new_callable=AsyncMock)
@patch('app.plugins.code_modifier_plugin.subprocess.run') # Mocks subprocess.run called by plugin
@patch('app.plugins.code_modifier_plugin.CODEBASE_PATH', new_callable=lambda: None) # Will be replaced by temp_codebase
@patch('app.services.orchestration_service.CODEBASE_PATH', new_callable=lambda: None) # Also in orchestrator for git ops
def test_code_modifier_plugin_full_flow(
    mock_orchestrator_codebase_path, # Order of patch args is inner-most first
    mock_plugin_codebase_path,
    mock_subprocess_run,
    mock_ollama_generate_json,
    admin_headers_agent,
    test_db_agent_session: SQLAlchemySession,
    temp_codebase # Use the temp codebase fixture
):
    """
    Test the CodeModifierPlugin's successful execution path, including file operations,
    formatting, diffing, and simulated testing, using mocks for external services.
    """
    # Set the mocked CODEBASE_PATH to our temporary directory
    mock_plugin_codebase_path.return_value = temp_codebase # This doesn't work for module const
    mock_orchestrator_codebase_path.return_value = temp_codebase
    
    # Replace the actual CODEBASE_PATH constants in the modules for the duration of this test
    with patch('app.plugins.code_modifier_plugin.CODEBASE_PATH', temp_codebase), \
         patch('app.services.orchestration_service.CODEBASE_PATH', temp_codebase):

        # --- Mock Setup ---
        # Mock Ollama LLM response
        mock_ollama_generate_json.return_value = {
            "explanation": "Refactored sample_service.py to include a new greeting.",
            "modifications": [{
                "file_path": "backend/app/sample_service.py", # Path relative to temp_codebase
                "new_code": "def new_greeting():\n    return 'Hello, Frankie Agent!'"
            }]
        }

        # Mock subprocess.run for formatting (Prettier) and testing (pytest)
        def subprocess_side_effect_configured(*args, **kwargs):
            command_args = args[0]
            # For Prettier (example, if a .js file was targeted)
            if "npx" in command_args and "prettier" in command_args:
                # Simulate prettier modifying the temp file it was given
                # The plugin writes to a temp file, then calls prettier on it.
                # This mock just needs to return success.
                mock_res_format = MagicMock()
                mock_res_format.returncode = 0
                mock_res_format.stdout = "" # Prettier --write modifies in place
                mock_res_format.stderr = ""
                return mock_res_format
            # For pytest
            elif "pytest" in command_args:
                mock_res_test = MagicMock()
                mock_res_test.returncode = 0 # 0 for pass
                mock_res_test.stdout = "=== 10 tests passed in 0.5s ==="
                mock_res_test.stderr = ""
                return mock_res_test
            # Fallback for any other subprocess call (shouldn't happen in this plugin's flow)
            return MagicMock(returncode=1, stderr="Mocked subprocess: Unknown command")
        mock_subprocess_run.side_effect = subprocess_side_effect_configured
        
        # --- Test Execution ---
        # 1. Create a permission for the target file within the temp_codebase context
        #    Paths in permissions should be relative to the project root (which temp_codebase mimics)
        permission_data = schemas.AgentPermissionCreate(path="backend/app/sample_service.py", comment="Test permission for sample_service.py").dict()
        perm_response = client.post(f"{settings.API_V1_STR}/admin/agent/permissions", json=permission_data, headers=admin_headers_agent)
        assert perm_response.status_code == 201, f"Permission creation failed: {perm_response.text}"

        # 2. Create the agent task targeting the file in temp_codebase
        task_create_data = schemas.AgentTaskCreate(
            prompt="Refactor sample_service.py to add a new greeting function.",
            plugin_id="code_modifier",
            target_files="backend/app/sample_service.py" # Relative to project root
        ).dict()

        create_task_response = client.post(
            f"{settings.API_V1_STR}/admin/agent/tasks",
            json=task_create_data,
            headers=admin_headers_agent
        )
        assert create_task_response.status_code == 202, f"Task creation failed: {create_task_response.text}"
        task_id = create_task_response.json()["id"]

        # 3. Simulate background task completion by waiting and then fetching the task
        #    A more robust way would be to execute the background task synchronously in tests.
        import time; time.sleep(2) # Crude wait for background task processing
        
        get_task_response = client.get(f"{settings.API_V1_STR}/admin/agent/tasks/{task_id}", headers=admin_headers_agent)
        assert get_task_response.status_code == 200, f"Failed to get task details: {get_task_response.text}"
        task_result = get_task_response.json()

        # 4. Assertions on the task result
        assert task_result["status"] == models.TaskStatus.AWAITING_REVIEW.value
        assert task_result["llm_explanation"] == "Refactored sample_service.py to include a new greeting."
        assert "def new_greeting():" in task_result["proposed_diff"] # Black formatted this
        assert "return 'Hello, Frankie Agent!'" in task_result["proposed_diff"]
        assert task_result["test_status"] == models.TestStatus.PASS.value
        assert "10 tests passed" in task_result["test_results"]

        # Verify mocks were called as expected
        mock_ollama_generate_json.assert_called_once()
        # At least one call for pytest, maybe for prettier if it was triggered (depends on formatter logic)
        assert mock_subprocess_run.call_count >= 1