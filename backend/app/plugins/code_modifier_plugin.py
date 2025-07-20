import os
import pathlib
import subprocess
import tempfile
import time
import difflib
import black # For formatting Python code
from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from loguru import logger
from typing import Dict, List, Any # For type hinting

from app.plugins.base_plugin import FrankiePlugin
from app.services.ollama_service import ollama_service
from app.db import models, crud, schemas  # Ensure crud and schemas are imported
from app.core.config import settings

# Root of the repository that the plugin modifies
CODEBASE_PATH = settings.CODEBASE_PATH

class CodeModifierPlugin(FrankiePlugin):
    """
    A plugin for modifying the application's own codebase using LLM suggestions,
    including automated formatting and testing.
    """

    def __init__(self, db, task):
        super().__init__(db, task)
        self.repo: Repo | None = None # Initialize repo attribute
        try:
            # Ensure the codebase path actually exists before trying to init Repo
            if os.path.isdir(CODEBASE_PATH):
                self.repo = Repo(CODEBASE_PATH)
            else:
                 logger.error(f"CodeModifierPlugin: Codebase path '{CODEBASE_PATH}' does not exist or is not a directory. Git operations will be disabled for task {self.task.id}.")
        except InvalidGitRepositoryError:
            logger.error(f"CodeModifierPlugin: Directory {CODEBASE_PATH} is not a valid Git repository for task {self.task.id}. Code modification features requiring Git will fail.")
        except NoSuchPathError:
            logger.error(f"CodeModifierPlugin: Path {CODEBASE_PATH} for Git repository does not exist for task {self.task.id}. Git operations will be disabled.")
        except Exception as e:
            logger.error(f"CodeModifierPlugin: Failed to initialize Git repo at {CODEBASE_PATH} for task {self.task.id}: {e}")


    @staticmethod
    def get_id() -> str:
        return "code_modifier"

    @staticmethod
    def get_name() -> str:
        return "Code Modifier"
    
    @staticmethod
    def get_description() -> str:
        return "Analyzes natural language prompts to suggest, format, test, and (upon approval) apply code modifications to the project."

    def _check_permissions(self, file_paths: List[str]):
        """Checks if the agent has permission to access all specified file paths."""
        if not file_paths:
            raise ValueError("No target files specified for permission check.") # Or handle as no-op if appropriate
            
        allowed_permissions: List[models.AgentPermission] = crud.get_permissions(self.db, limit=1000)
        allowed_path_strings: set[str] = {p.path for p in allowed_permissions}

        for target_file_path_str in file_paths:
            normalized_target_path = pathlib.Path(target_file_path_str.strip()).as_posix()
            
            is_currently_allowed = False
            for allowed_path_rule_str in allowed_path_strings:
                normalized_allowed_rule = pathlib.Path(allowed_path_rule_str.strip()).as_posix()
                
                if normalized_allowed_rule.endswith('/'): # Directory rule
                    if normalized_target_path.startswith(normalized_allowed_rule):
                        is_currently_allowed = True
                        break
                elif normalized_target_path == normalized_allowed_rule: # Exact file match
                    is_currently_allowed = True
                    break
            
            if not is_currently_allowed:
                error_msg = f"Agent permission denied for '{normalized_target_path}'. Please add this path or a parent directory (ending with '/') to the allowed paths in admin settings."
                logger.warning(f"Permission denied for task {self.task.id}: {error_msg}")
                raise PermissionError(error_msg)
        logger.info(f"Permissions check passed for task {self.task.id} on files: {file_paths}")

    def _read_files(self, target_file_paths: List[str]) -> Dict[str, str]:
        """Reads content of specified files, ensuring they are within the designated codebase."""
        files_content_map: Dict[str, str] = {}
        if not target_file_paths:
            return files_content_map

        for rel_path_str in target_file_paths:
            clean_rel_path = rel_path_str.strip()
            # Construct full path and normalize it to prevent directory traversal issues
            # os.path.join correctly handles path components.
            # os.path.normpath resolves '..' and '.' segments.
            full_path = os.path.normpath(os.path.join(CODEBASE_PATH, clean_rel_path))
            
            # Security check: ensure the resolved absolute path is still within CODEBASE_PATH
            if not os.path.abspath(full_path).startswith(os.path.abspath(CODEBASE_PATH)):
                raise PermissionError(f"Attempt to access file outside designated codebase via path: '{clean_rel_path}' resolved to '{full_path}'")

            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        files_content_map[clean_rel_path] = f.read()
                except Exception as e:
                    logger.error(f"Error reading file {full_path} for task {self.task.id}: {e}")
                    raise FileNotFoundError(f"Could not read target file: '{clean_rel_path}'. Error: {e}")
            else:
                logger.info(f"Target file '{clean_rel_path}' (resolved to '{full_path}') not found for task {self.task.id}. Assuming it's a new file to be created.")
                files_content_map[clean_rel_path] = "" # Provide empty content for new files to allow diff generation
        return files_content_map

    def _generate_meta_prompt(self, user_prompt: str, files_content: Dict[str, str]) -> str:
        """Constructs the detailed prompt for the LLM for code modification."""
        file_blocks_str = "\n\n".join(
            [f"--- START FILE: {path} ---\n\n{content}\n\n--- END FILE: {path} ---" 
             for path, content in files_content.items() if content.strip()] # Only include files with actual content for existing
        )
        if not files_content or not file_blocks_str.strip():
            file_blocks_str = ("No existing file content provided. "
                               "If target files were specified, you might be creating new files. "
                               "Refer to the user request for desired new file paths and content.")
            
        # Guidance on file paths to use in LLM response
        target_files_list_str = ", ".join(files_content.keys()) if files_content else "as per user request for new files"
            
        return f"""You are Frankie, an expert AI software engineer. Your task is to modify source code based on a user request.

        **CRITICAL INSTRUCTIONS FOR YOUR RESPONSE:**
        1.  **JSON Format:** Your ENTIRE response MUST be a single, valid JSON object. No text before or after it.
        2.  **JSON Keys:** The JSON object must have exactly two top-level keys:
            * `"explanation"`: A string containing a Markdown-formatted explanation of your proposed changes. Describe your plan, the files you'll modify (or create), and the reasoning behind your approach.
            * `"modifications"`: An array of objects. Each object in this array represents a file to be modified or created.
        3.  **Modification Object Keys:** Each object within the "modifications" array must have exactly two keys:
            * `"file_path"`: A string representing the full relative path of the file from the project root (e.g., `backend/app/main.py`, `frontend/src/components/MyComponent.jsx`).
            * `"new_code"`: A string containing the ENTIRE, complete, updated source code for that file. **Do NOT provide partial code, snippets, or diffs.** If creating a new file, this is its full content.

        **USER REQUEST:**
        "{user_prompt}"

        **TARGET FILES AND THEIR CURRENT CONTENT (if existing, paths are relative to project root):**
        (Files listed here are: {target_files_list_str})
        {file_blocks_str}

        Analyze the request and the provided file contents. Then, generate the JSON response as specified.
        If the request implies creating a new file, ensure its path is correct and provide its full content in "new_code".
        If a target file was not found and you are not creating it, note this in your explanation.
        """

    def _format_code(self, file_path_str: str, code_content: str) -> str:
        """Formats a string of code using Black for Python or Prettier for frontend files."""
        # ... (Implementation is identical to the one provided in the previous "Part 4: Auto-formatting/Linting" step)
        # ... (Ensure it uses self.task.id for logging if needed, and CODEBASE_PATH)
        # For brevity, re-pasting the core logic:
        file_path = pathlib.Path(file_path_str)
        file_extension = file_path.suffix
        logger.info(f"Attempting to format code for file: {file_path_str} (extension: {file_extension}) for task {self.task.id}")
        original_code_content = code_content # Keep original if formatting fails

        try:
            if file_extension == ".py":
                return black.format_str(code_content, mode=black.Mode())
            elif file_extension in ['.js', '.jsx', '.ts', '.tsx', '.json', '.css', '.scss', '.html', '.md']:
                frontend_dir = os.path.normpath(os.path.join(CODEBASE_PATH, "frontend"))
                if not os.path.isdir(frontend_dir):
                     logger.warning(f"Frontend directory {frontend_dir} not found. Cannot run Prettier for {file_path_str}. Skipping format.")
                     return original_code_content
                
                with tempfile.NamedTemporaryFile(
                    mode='w+', suffix=file_extension, dir=frontend_dir, delete=False, encoding='utf-8' # Temp file in frontend dir
                ) as tmp_file:
                    tmp_file.write(code_content)
                    tmp_file_path_abs = tmp_file.name
                
                prettier_command = [ "npx", "prettier", "--write", tmp_file_path_abs ]
                process = subprocess.run(prettier_command, capture_output=True, text=True, cwd=frontend_dir, timeout=60)
                
                if process.returncode == 0:
                    with open(tmp_file_path_abs, 'r', encoding='utf-8') as f:
                        formatted_content = f.read()
                    logger.info(f"Prettier successfully formatted {file_path_str}")
                    os.remove(tmp_file_path_abs)
                    return formatted_content
                else:
                    logger.warning(f"Prettier failed for {file_path_str}. Stderr: {process.stderr or 'None'}. Stdout: {process.stdout or 'None'}")
                    os.remove(tmp_file_path_abs)
                    return original_code_content
            else:
                logger.info(f"No formatter for extension '{file_extension}' of file {file_path_str}.")
                return original_code_content
        except Exception as e:
            logger.error(f"Failed to format code for {file_path_str}: {e}", exc_info=True)
            if 'tmp_file_path_abs' in locals() and os.path.exists(tmp_file_path_abs):
                try: os.remove(tmp_file_path_abs)
                except Exception as e_clean: logger.error(f"Error cleaning temp format file {tmp_file_path_abs}: {e_clean}")
            return original_code_content


    def _format_modifications(self, modifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Applies formatting to all proposed code modifications from the LLM."""
        formatted_mods = []
        for mod in modifications:
            file_path = mod.get("file_path")
            new_code = mod.get("new_code")
            if file_path and isinstance(new_code, str):
                formatted_code = self._format_code(file_path, new_code)
                formatted_mods.append({"file_path": file_path, "new_code": formatted_code})
            else:
                logger.warning(f"Skipping formatting for invalid/incomplete modification entry: {mod} in task {self.task.id}")
                formatted_mods.append(mod) # Pass through if malformed
        return formatted_mods

    def _generate_diff(self, formatted_modifications: List[Dict[str, Any]], original_files_content: Dict[str, str]) -> str:
        """Generates a unified diff string for all formatted modifications against their originals."""
        full_diff_lines: List[str] = []
        for mod in formatted_modifications:
            file_path = mod.get("file_path")
            new_code_str = mod.get("new_code", "") # Default to empty if new_code is missing or not string

            if not file_path:
                logger.warning(f"Modification entry missing 'file_path' in task {self.task.id}. Skipping diff for this entry: {mod}")
                continue
            if not isinstance(new_code_str, str):
                logger.warning(f"Modification entry 'new_code' is not a string for file '{file_path}' in task {self.task.id}. Using empty string for diff.")
                new_code_str = ""

            original_code_str = original_files_content.get(file_path, "") # Empty if it's a new file being created

            # Create diff lines
            diff_iter = difflib.unified_diff(
                original_code_str.splitlines(keepends=True),
                new_code_str.splitlines(keepends=True),
                fromfile=f"a/{file_path}", # Standard git diff "from" prefix
                tofile=f"b/{file_path}",   # Standard git diff "to" prefix
                lineterm=""                # Avoids adding extra newlines in diff output
            )
            for line in diff_iter:
                full_diff_lines.append(line) # Append line by line (already has newline if keepends=True)
        
        return "".join(full_diff_lines) if full_diff_lines else "-- No textual changes detected or no modifications proposed --"


    def _run_tests_on_changes(self, proposed_diff: str) -> Dict[str, Any]:
        """Applies changes to a temporary git branch, runs backend tests, and cleans up."""
        if not self.repo:
            logger.error(f"Git repository not available for testing task {self.task.id}.")
            return {"status": models.TestStatus.FAIL, "results": "Git repository not initialized for testing."}

        original_branch_name = ""
        try:
            original_branch_name = self.repo.active_branch.name
        except TypeError: # Handles detached HEAD state
             original_branch_name = self.repo.head.commit.hexsha 
             logger.warning(f"Repo is in detached HEAD state ({original_branch_name}). Will attempt to checkout a new branch and return here.")


        temp_branch_name = f"frankie-task-test-{self.task.id}-{int(time.time())}"
        patch_file_path = "" # Define for finally block

        try:
            if self.repo.is_dirty(untracked_files=True):
                logger.warning(f"Repo is dirty before testing task {self.task.id}. Stashing changes on current branch '{original_branch_name}'.")
                self.repo.git.stash("push", "-u", "-m", f"frankie-autostash-test-{self.task.id}")

            temp_branch = self.repo.create_head(temp_branch_name)
            temp_branch.checkout()
            logger.info(f"Checked out temporary branch '{temp_branch_name}' for testing task {self.task.id}.")
            
            if proposed_diff and proposed_diff.strip() and proposed_diff.strip() != "-- No textual changes detected or no modifications proposed --":
                # Use a temporary file within CODEBASE_PATH for git apply, as it resolves paths relative to repo root
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.patch', dir=CODEBASE_PATH, encoding='utf-8') as patch_file:
                    patch_file.write(proposed_diff)
                    patch_file_path = patch_file.name
                
                # Apply the patch using git apply
                self.repo.git.apply(patch_file_path, '--recount', '--inaccurate-eof', '--allow-empty')
                logger.info(f"Applied diff to temporary branch '{temp_branch_name}' for task {self.task.id}.")
            else:
                logger.info(f"No diff content to apply for testing task {self.task.id}. Running tests on current state of branch '{temp_branch_name}'.")

            # Run pytest for backend tests
            backend_dir = os.path.normpath(os.path.join(CODEBASE_PATH, "backend"))
            if not os.path.isdir(backend_dir):
                 return {"status": models.TestStatus.FAIL, "results": f"Backend directory '{backend_dir}' not found for running tests."}

            logger.info(f"Running pytest in {backend_dir} for task {self.task.id}...")
            process = subprocess.run(
                ["python", "-m", "pytest"], # Runs all tests found by pytest in cwd
                cwd=backend_dir,
                capture_output=True,
                text=True,
                timeout=300 # 5 minute timeout for tests
            )
            test_output = f"--- PYTEST STDOUT ---\n{process.stdout}\n\n--- PYTEST STDERR ---\n{process.stderr}"
            
            if process.returncode == 0:
                logger.info(f"Backend tests PASSED for task {self.task.id} on branch {temp_branch_name}.")
                return {"status": models.TestStatus.PASS, "results": test_output}
            else:
                logger.warning(f"Backend tests FAILED for task {self.task.id} on branch {temp_branch_name}. Exit code: {process.returncode}")
                return {"status": models.TestStatus.FAIL, "results": test_output}

        except GitCommandError as e:
            logger.error(f"Git command error during testing for task {self.task.id}: {e.stderr or e.stdout}")
            return {"status": models.TestStatus.FAIL, "results": f"Git command failed during testing: {e.stderr or e.stdout}"}
        except Exception as e:
            logger.error(f"Unexpected error during testing for task {self.task.id}: {e}", exc_info=True)
            return {"status": models.TestStatus.FAIL, "results": f"An unexpected error occurred during testing: {str(e)}"}
        finally:
            if self.repo: # Ensure repo was initialized
                logger.info(f"Cleaning up after test run for task {self.task.id}. Attempting to switch back to {original_branch_name}.")
                try:
                    self.repo.git.checkout(original_branch_name, force=True) # Force checkout to discard any uncommitted changes on temp_branch
                    self.repo.delete_head(temp_branch_name, force=True)
                    logger.info(f"Successfully cleaned up temporary branch '{temp_branch_name}'.")
                except GitCommandError as e_cleanup:
                    logger.error(f"Could not fully cleanup temporary test branch '{temp_branch_name}': {e_cleanup.stderr}")
            if patch_file_path and os.path.exists(patch_file_path):
                try: os.remove(patch_file_path)
                except OSError as e_ose: logger.error(f"Error deleting patch file {patch_file_path}: {e_ose}")


    async def execute(self) -> dict:
        """Main execution logic for the CodeModifierPlugin."""
        logger.info(f"Executing CodeModifierPlugin for task {self.task.id} with prompt: '{self.task.prompt[:100]}...'")
        
        if not self.task.target_files: # target_files is a string
            logger.error(f"Task {self.task.id}: Target files string is missing for Code Modifier plugin.")
            return {"status": models.TaskStatus.ERROR, "error_message": "Target files must be specified as a comma-separated string for the Code Modifier plugin."}
        
        target_file_paths = [p.strip() for p in self.task.target_files.split(',') if p.strip()]
        if not target_file_paths:
             logger.error(f"Task {self.task.id}: No valid target files were parsed from '{self.task.target_files}'.")
             return {"status": models.TaskStatus.ERROR, "error_message": "No valid target files were specified after parsing the input string."}

        try:
            self._check_permissions(target_file_paths)
            original_files_content = self._read_files(target_file_paths)
            meta_prompt = self._generate_meta_prompt(self.task.prompt, original_files_content)
            
            logger.info(f"Sending meta-prompt to LLM for task {self.task.id}...")
            llm_response = await ollama_service.generate_json(meta_prompt)

            if "error" in llm_response: # Check for error key from OllamaService
                raise ValueError(f"LLM generation failed: {llm_response['error']}")

            explanation = llm_response.get("explanation", "No explanation provided by LLM.")
            modifications: List[Dict[str, Any]] = llm_response.get("modifications", [])
            
            if not modifications: # Check if modifications list is empty or missing
                logger.info(f"LLM did not propose any code modifications for task {self.task.id}.")
                return {
                    "status": models.TaskStatus.AWAITING_REVIEW,
                    "llm_explanation": explanation + "\n\n(No code modifications were proposed by the LLM.)",
                    "proposed_diff": "-- No changes proposed by LLM --",
                    "test_status": models.TestStatus.NOT_RUN,
                    "test_results": "No code changes proposed by LLM, so no tests were run."
                }
            
            logger.info(f"LLM proposed {len(modifications)} modifications for task {self.task.id}. Formatting code...")
            formatted_modifications = self._format_modifications(modifications)
            
            logger.info(f"Generating diff for task {self.task.id}...")
            full_diff = self._generate_diff(formatted_modifications, original_files_content)
            
            logger.info(f"Running tests for task {self.task.id}...")
            test_run_result = self._run_tests_on_changes(full_diff)
            
            logger.info(f"Task {self.task.id} ready for review. Test status: {test_run_result.get('status', models.TestStatus.FAIL).value}")
            return {
                "status": models.TaskStatus.AWAITING_REVIEW,
                "llm_explanation": explanation,
                "proposed_diff": full_diff,
                "test_status": test_run_result.get("status", models.TestStatus.FAIL),
                "test_results": test_run_result.get("results", "Error during test execution phase."),
            }
        except FileNotFoundError as e:
            logger.error(f"File not found error processing task {self.task.id}: {e}")
            return {"status": models.TaskStatus.ERROR, "error_message": str(e)}
        except PermissionError as e:
            logger.error(f"Permission error processing task {self.task.id}: {e}")
            return {"status": models.TaskStatus.ERROR, "error_message": str(e)}
        except ValueError as e: # For LLM errors or other value issues
            logger.error(f"Value error during task {self.task.id}: {e}")
            return {"status": models.TaskStatus.ERROR, "error_message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error executing CodeModifierPlugin for task {self.task.id}: {e}", exc_info=True)
            return {"status": models.TaskStatus.ERROR, "error_message": f"An unexpected error occurred during plugin execution: {str(e)}"}