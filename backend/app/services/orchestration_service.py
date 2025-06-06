from sqlalchemy.orm import Session
from loguru import logger
from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError # Import Git exceptions
import os

from app.db import models, crud
from app.services.plugin_manager import get_plugin_manager # Function to get the initialized manager
from app.services.notification_service import notification_service # Import the global instance

CODEBASE_PATH = "/frankie_codebase/" # Should match docker-compose volume mount

class AgentOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.plugin_manager = get_plugin_manager() # Get the globally initialized PluginManager
        self.repo: Repo | None = None # Type hint for self.repo
        try:
            # Ensure the codebase path actually exists before trying to init Repo
            if os.path.isdir(CODEBASE_PATH):
                self.repo = Repo(CODEBASE_PATH)
            else:
                logger.error(f"Orchestrator: Codebase path '{CODEBASE_PATH}' does not exist or is not a directory. Git operations will be disabled.")
        except InvalidGitRepositoryError:
            logger.error(f"Orchestrator: Directory {CODEBASE_PATH} is not a valid Git repository. Code modification features will fail for git operations.")
        except NoSuchPathError: # More specific exception if path doesn't exist
            logger.error(f"Orchestrator: Path {CODEBASE_PATH} for Git repository does not exist. Git operations will be disabled.")
        except Exception as e: # Catch other potential errors during Repo initialization
            logger.error(f"Orchestrator: Failed to initialize Git repo at {CODEBASE_PATH}: {e}")

    async def execute_task(self, task_id: int):
        """
        High-level orchestrator that finds the right plugin and executes the task.
        Updates the task record with results from the plugin.
        """
        db_task = crud.get_agent_task(self.db, task_id=task_id)
        if not db_task:
            logger.error(f"Task {task_id} not found for execution.")
            return

        if not db_task.plugin_id:
            error_msg = f"Task #{task_id} does not have a plugin_id specified. Cannot determine which plugin to run."
            logger.error(error_msg)
            crud.update_agent_task(self.db, db_task=db_task, task_update_data={"status": models.TaskStatus.ERROR, "error_message": error_msg})
            notification_service.notify_task_status_change(db_task) # Notify about the error
            return

        plugin_class = self.plugin_manager.get_plugin_class(db_task.plugin_id)
        if not plugin_class:
            error_msg = f"Plugin with ID '{db_task.plugin_id}' not found for task #{task_id}. Task cannot be executed."
            logger.error(error_msg)
            crud.update_agent_task(self.db, db_task=db_task, task_update_data={"status": models.TaskStatus.ERROR, "error_message": error_msg})
            notification_service.notify_task_status_change(db_task)
            return

        # Set task status to ANALYZING before starting plugin execution
        crud.update_agent_task(self.db, db_task=db_task, task_update_data={"status": models.TaskStatus.ANALYZING})
        
        plugin_execution_results = {} # To store what the plugin returns
        try:
            logger.info(f"Executing plugin '{db_task.plugin_id}' for task #{task_id} (Prompt: '{db_task.prompt[:100]}...').")
            plugin_instance = plugin_class(db=self.db, task=db_task)
            plugin_execution_results = await plugin_instance.execute() # Plugin returns a dict of fields to update
        except Exception as e:
            logger.error(f"Plugin execution failed catastrophically for task #{task_id} (Plugin: {db_task.plugin_id}): {e}", exc_info=True)
            plugin_execution_results = {"status": models.TaskStatus.ERROR, "error_message": f"Critical plugin execution error: {str(e)}"}
        
        # Update the task with the results from the plugin
        crud.update_agent_task(self.db, db_task=db_task, task_update_data=plugin_execution_results)
        
        # Refresh db_task to get the latest status before sending notification
        # This is important because the plugin_execution_results dict might change the status.
        self.db.refresh(db_task) 
        notification_service.notify_task_status_change(db_task)
        logger.info(f"Task #{task_id} (Plugin: {db_task.plugin_id}) processing finished with status: {db_task.status.value}")
    
    def apply_and_commit_changes(self, task: models.AgentTask, user: models.User) -> str:
        """
        Applies changes from a task's proposed_diff (if it's a 'code_modifier' task) 
        and commits them to the Git repository.
        """
        if task.plugin_id != "code_modifier":
            logger.warning(f"Attempted to apply git commit for task {task.id} with non-code_modifier plugin: {task.plugin_id}.")
            raise ValueError(f"Git commit is only applicable for 'code_modifier' plugin tasks. Task plugin: {task.plugin_id}")

        if not self.repo:
            logger.error(f"Cannot apply and commit changes for task {task.id}: Git repository not available.")
            raise RuntimeError("Git repository not found or not initialized. Check backend startup logs.")
        if not task.proposed_diff or not task.proposed_diff.strip(): # Check if diff is empty or only whitespace
            logger.warning(f"Task {task.id} (code_modifier) has no proposed_diff or an empty diff to apply. No git action taken.")
            # Consider this a success without commit or a specific status.
            # For now, raise an error as 'approve' implies changes.
            raise ValueError("Task has no actual proposed changes (diff) to apply.")

        # Use a temporary file within the repo for the patch to ensure paths are relative to repo root
        patch_file_name = f"frankie_task_{task.id}_apply.patch"
        patch_file_path = os.path.join(CODEBASE_PATH, patch_file_name) 

        try:
            with open(patch_file_path, "w", encoding='utf-8') as f:
                f.write(task.proposed_diff)

            # Ensure repo is clean before applying patch to avoid conflicts with unrelated local changes
            if self.repo.is_dirty(untracked_files=True):
                logger.warning(f"Repository is dirty before applying patch for task {task.id}. Attempting to stash uncommitted changes.")
                # Stash any local changes. A more robust system might fail here or require manual intervention.
                self.repo.git.stash("push", "-u", "-m", f"frankie-autostash-before-apply-task-{task.id}")

            # Apply the patch. `git apply` can handle creating new files if the diff format is correct (e.g. from `git diff`).
            # --recount: Useful with whitespace issues.
            # --inaccurate-eof: Handles patches that might not end with a newline.
            # --allow-empty: Allows applying a patch that results in no changes.
            self.repo.git.apply(patch_file_path, '--recount', '--inaccurate-eof', '--allow-empty')
            logger.info(f"Successfully applied patch for task {task.id} using temporary file: {patch_file_path}")
            
            # Check if the patch actually resulted in changes to be committed
            if not self.repo.is_dirty(untracked_files=True) and not self.repo.index.diff("HEAD"):
                 logger.info(f"No actual changes to commit for task {task.id} after applying patch. The patch might have been empty or resulted in no change to tracked files.")
                 return "No changes to commit after patch application." # Return specific message

            # Stage all changes (including new files if the patch created them and they are tracked)
            self.repo.git.add(A=True) 
            
            commit_message = f"feat(agent): Task #{task.id} - {task.plugin_id}\n\nPrompt: {task.prompt}\nApproved and applied by: {user.email}"
            commit = self.repo.index.commit(commit_message, author=f"{user.full_name or user.email} <{user.email}>")
            
            logger.info(f"Committed changes for task {task.id} with hash {commit.hexsha}")
            return commit.hexsha
        
        except GitCommandError as e:
            logger.error(f"Git command failed during apply/commit for task {task.id}: CMD: {e.command}, STDERR: {e.stderr}")
            try:
                # Attempt to clean up any partially applied patch by resetting the working directory
                self.repo.git.reset('--hard', 'HEAD') # Reset to the last commit
                logger.info(f"Attempted to hard reset repo to HEAD after failed patch apply for task {task.id}.")
            except GitCommandError as reset_e:
                logger.error(f"Failed to reset repo after patch failure for task {task.id}: {reset_e.stderr}")
            raise GitCommandError(e.command, e.status, e.stdout, e.stderr) # Re-raise the original error with details
        finally:
            if os.path.exists(patch_file_path):
                try:
                    os.remove(patch_file_path)
                except OSError as e_remove:
                    logger.error(f"Error removing temporary patch file {patch_file_path}: {e_remove}")