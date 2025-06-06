from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any 
import json # For loading/saving task_context_data

from app.core.dependencies import get_db, get_current_admin_user
from app.db import schemas, crud, models
from app.services.orchestration_service import AgentOrchestrator
from app.services.plugin_manager import get_plugin_manager 
from app.services.notification_service import notification_service 
from app.core.config import settings, NotificationSettingsModel 
from loguru import logger 

# Import Odyssey Plugin phase constants for clarity
from app.plugins.odyssey_plugin import (
    ODYSSEY_PHASE_PLANNING, 
    ODYSSEY_PHASE_AWAITING_PLAN_REVIEW, 
    ODYSSEY_PHASE_EXECUTING_MILESTONE,
    ODYSSEY_PHASE_AWAITING_MILESTONE_REVIEW,
    ODYSSEY_PHASE_FINALIZING,
    ODYSSEY_PHASE_AWAITING_FINAL_REVIEW,
    ODYSSEY_PHASE_COMPLETED
)


router = APIRouter()

# ... (User Management, other Agent Task Endpoints, Plugin Listing, Permissions, Settings endpoints remain the same as Part 6) ...
# For brevity, only showing the modified approve endpoint and relevant parts.
# Ensure all previous endpoints from Part 6 are present in the full file.

@router.get("/users", response_model=List[schemas.UserPublic]) # From Part 6
def list_all_users_admin(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    return crud.get_users(db, skip=skip, limit=limit)

@router.post("/agent/tasks", response_model=schemas.AgentTask, status_code=status.HTTP_202_ACCEPTED) # From Part 6
def create_new_agent_task(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user), task_in: schemas.AgentTaskCreate = Body(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    # (Logic from Part 6 for validation based on plugin_id)
    if task_in.plugin_id == "code_modifier" and not task_in.target_files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target files must be specified for 'code_modifier'.")
    if task_in.plugin_id == "genealogy_researcher" and task_in.target_person_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target person ID must be specified for 'genealogy_researcher'.")
    if task_in.plugin_id == "odyssey_agent" and not task_in.prompt.strip():
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A detailed prompt is required for the Odyssey Agent.")

    task = crud.create_agent_task(db=db, task_in=task_in, owner_id=current_user.id)
    orchestrator = AgentOrchestrator(db=db)
    # For Odyssey, initial status is PENDING, orchestrator will call plugin, plugin sets to AWAITING_PLAN_REVIEW
    background_tasks.add_task(orchestrator.execute_task, task_id=task.id)
    return task

@router.get("/agent/tasks", response_model=List[schemas.AgentTask]) # From Part 6
def list_agent_tasks_for_admin(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user), skip: int = 0, limit: int = 20):
    return crud.get_agent_tasks_by_owner(db=db, owner_id=current_user.id, skip=skip, limit=limit)

@router.get("/agent/tasks/{task_id}", response_model=schemas.AgentTask) # From Part 6
def get_specific_agent_task_details(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    task = crud.get_agent_task(db=db, task_id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not owned by admin.")
    return task

# --- MODIFIED: Agent Task Approval Endpoint ---
@router.post("/agent/tasks/{task_id}/approve", response_model=schemas.AgentTask)
def approve_and_process_agent_task( # Renamed to be more generic
    task_id: int,
    background_tasks: BackgroundTasks, # To re-queue Odyssey tasks
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
    # Optional body for providing feedback or specific approval parameters
    # approval_data: Optional[Dict[str, Any]] = Body(None) 
):
    """
    Approve an agent task that is AWAITING_REVIEW.
    - For 'code_modifier': Applies proposed code changes and commits them.
    - For 'odyssey_agent': Approves the current plan or milestone, transitioning it to the next execution phase.
    - For other plugins: Marks the task as applied.
    Requires admin privileges.
    """
    task = crud.get_agent_task(db=db, task_id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not owned by current admin.")
    
    if task.status != models.TaskStatus.AWAITING_REVIEW:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task is not awaiting review. Current status: {task.status.value}")
    
    orchestrator = AgentOrchestrator(db=db)
    updated_task_data = {} # To store fields for task update

    try:
        if task.plugin_id == "odyssey_agent":
            logger.info(f"Admin {current_user.email} approving Odyssey task #{task.id}.")
            task_context = json.loads(task.task_context_data) if task.task_context_data else {}
            current_phase = task_context.get("current_phase", ODYSSEY_PHASE_PLANNING)

            if current_phase == ODYSSEY_PHASE_AWAITING_PLAN_REVIEW:
                task_context["current_phase"] = ODYSSEY_PHASE_EXECUTING_MILESTONE
                task_context["current_milestone_index"] = 0 # Start with the first milestone
                logger.info(f"Odyssey task #{task.id} plan approved. Transitioning to execute milestone 0.")
            elif current_phase == ODYSSEY_PHASE_AWAITING_MILESTONE_REVIEW:
                current_milestone_idx = task_context.get("current_milestone_index", -1)
                plan_milestones = task_context.get("plan", {}).get("milestones", [])
                if 0 <= current_milestone_idx < len(plan_milestones) - 1:
                    task_context["current_milestone_index"] = current_milestone_idx + 1
                    task_context["current_phase"] = ODYSSEY_PHASE_EXECUTING_MILESTONE
                    logger.info(f"Odyssey task #{task.id} milestone {current_milestone_idx} approved. Transitioning to milestone {current_milestone_idx + 1}.")
                else: # Last milestone was reviewed and approved
                    task_context["current_phase"] = ODYSSEY_PHASE_FINALIZING
                    logger.info(f"Odyssey task #{task.id} all milestones approved. Transitioning to finalizing phase.")
            # Add ODYSSEY_PHASE_AWAITING_FINAL_REVIEW if needed, which would transition to APPLIED
            else:
                # This case should ideally not be hit if UI enables approval only for AWAITING_X_REVIEW phases
                raise HTTPException(status_code=400, detail=f"Odyssey task is in an unexpected phase ('{current_phase}') for approval.")

            updated_task_data = {
                "status": models.TaskStatus.ANALYZING, # Set to a working status to be picked up by orchestrator
                "task_context_data": json.dumps(task_context)
            }
            updated_task = crud.update_agent_task(db, db_task=task, task_update_data=updated_task_data)
            # Re-queue the task for the orchestrator to execute the next phase
            background_tasks.add_task(orchestrator.execute_task, task_id=updated_task.id)
            # Notification will be sent by the plugin when it completes the next phase or errors
            return updated_task

        elif task.plugin_id == "code_modifier":
            # This part remains largely the same as before
            commit_hash = orchestrator.apply_and_commit_changes(task, current_user)
            updated_task_data = {"status": models.TaskStatus.APPLIED, "commit_hash": commit_hash}
            logger.info(f"CodeModifier task #{task.id} changes applied by admin {current_user.email}, commit: {commit_hash}.")
        
        else: # For other plugins like genealogy_researcher
            updated_task_data = {"status": models.TaskStatus.APPLIED}
            logger.info(f"Task #{task.id} (Plugin: {task.plugin_id}) marked as APPLIED by admin {current_user.email}.")

        updated_task = crud.update_agent_task(db, db_task=task, task_update_data=updated_task_data)
        notification_service.notify_task_status_change(updated_task)
        return updated_task

    except ValueError as ve: # Catch specific errors like no diff for code_modifier
        logger.warning(f"Approval error for task {task.id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        error_message = f"Failed to approve/process task #{task.id}: {str(e)}"
        logger.error(error_message, exc_info=True)
        task_after_error_update_data = {"status": models.TaskStatus.ERROR, "error_message": error_message}
        task_for_error_update = crud.get_agent_task(db, task_id=task_id)
        if task_for_error_update: # Re-fetch to ensure we have the latest state
            updated_task_on_error = crud.update_agent_task(db, db_task=task_for_error_update, task_update_data=task_after_error_update_data)
            notification_service.notify_task_status_change(updated_task_on_error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)


# ... (Plugin Listing, Permissions, Settings endpoints remain the same as Part 6) ...
@router.get("/agent/plugins", response_model=List[Dict[str, str]])
def list_all_available_agent_plugins(current_user: models.User = Depends(get_current_admin_user)):
    plugin_mgr = get_plugin_manager()
    return plugin_mgr.list_plugins()

@router.get("/agent/permissions", response_model=List[schemas.AgentPermission])
def read_all_code_agent_permissions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    return crud.get_permissions(db, skip=skip, limit=limit)

@router.post("/agent/permissions", response_model=schemas.AgentPermission, status_code=status.HTTP_201_CREATED)
def add_new_code_agent_permission(permission_in: schemas.AgentPermissionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    existing_permission = crud.get_permission_by_path(db, path=permission_in.path)
    if existing_permission:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Permission path '{permission_in.path}' already exists.")
    return crud.create_permission(db=db, permission_in=permission_in)

@router.delete("/agent/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_code_agent_permission(permission_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    permission_to_delete = crud.delete_permission(db=db, permission_id=permission_id)
    if not permission_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found.")
    return

@router.get("/settings/notifications", response_model=NotificationSettingsModel)
def get_application_notification_settings(current_user: models.User = Depends(get_current_admin_user)):
    return settings.notifications

@router.get("/agent/git/status", response_model=schemas.GitStatus)
def get_codebase_git_status(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    orchestrator = AgentOrchestrator(db=db)
    if not orchestrator.repo:
        raise HTTPException(status_code=503, detail="Git repository not available.")
    try: active_branch = orchestrator.repo.active_branch.name
    except TypeError: active_branch = orchestrator.repo.head.commit.hexsha[:12] + " (Detached HEAD)"
    return {"active_branch": active_branch, "latest_commit": orchestrator.repo.head.commit.hexsha[:7] if orchestrator.repo.head.is_valid() else None, "uncommitted_changes": orchestrator.repo.is_dirty(untracked_files=True)}