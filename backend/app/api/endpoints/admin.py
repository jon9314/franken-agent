from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
from loguru import logger

from app.core.dependencies import get_db, get_current_admin_user
from app.db import schemas, crud, models
from app.services.orchestration_service import AgentOrchestrator
from app.services.plugin_manager import get_plugin_manager
from app.services.notification_service import notification_service
from app.core.config import settings, NotificationSettingsModel

router = APIRouter()

@router.get("/users", response_model=List[schemas.UserPublic])
def list_all_users_admin(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_admin_user),
):
    """
    ADMIN ONLY: Retrieve all users.
    """
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.post("/users", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED)
def create_user_as_admin(
    *,
    db: Session = Depends(get_db),
    user_in: schemas.UserCreate, # Using the base UserCreate which now includes role
    current_user: models.User = Depends(get_current_admin_user),
):
    """
    ADMIN ONLY: Create a new user with a specific role.
    """
    user = crud.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    # The crud.create_user function can handle creating users with roles.
    new_user = crud.create_user(db, user=user_in)
    return new_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_as_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """
    ADMIN ONLY: Delete a user.
    """
    user_to_delete = crud.get_user(db, user_id=user_id)
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found.")

    if user_to_delete.id == current_user.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete their own account.")

    crud.delete_user(db, user_id=user_id)
    return

@router.post("/agent/tasks", response_model=schemas.AgentTask, status_code=status.HTTP_202_ACCEPTED)
async def create_new_agent_task(
    *,
    db: Session = Depends(get_db),
    task_in: schemas.AgentTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_admin_user),
):
    """
    ADMIN ONLY: Create a new task for an agent to execute.
    """
    task = crud.create_agent_task(db=db, task_in=task_in, owner_id=current_user.id)
    
    orchestrator = AgentOrchestrator(db=db)
    background_tasks.add_task(orchestrator.execute_task, task_id=task.id)
    
    return task

@router.get("/agent/tasks", response_model=List[schemas.AgentTask])
def list_agent_tasks_for_admin(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(get_current_admin_user),
):
    """
    ADMIN ONLY: Retrieve all agent tasks.
    """
    tasks = db.query(models.AgentTask).order_by(models.AgentTask.created_at.desc()).offset(skip).limit(limit).all()
    return tasks

@router.get("/agent/tasks/{task_id}", response_model=schemas.AgentTask)
def get_specific_agent_task_details(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """
    ADMIN ONLY: Retrieve the full details of a specific agent task.
    """
    task = crud.get_agent_task(db=db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task

@router.post("/agent/tasks/{task_id}/approve", response_model=schemas.AgentTask)
def approve_and_process_agent_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """
    ADMIN ONLY: Approves an agent task that is AWAITING_REVIEW.
    """
    task = crud.get_agent_task(db=db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    if task.status != models.TaskStatus.AWAITING_REVIEW:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task is not awaiting review. Current status: {task.status.value}")
    
    orchestrator = AgentOrchestrator(db=db)
    
    try:
        if task.plugin_id == "code_modifier":
            commit_hash = orchestrator.apply_and_commit_changes(task, current_user)
            update_data = {"status": models.TaskStatus.APPLIED, "commit_hash": commit_hash}
        elif task.plugin_id == "odyssey_agent":
             task_context = json.loads(task.task_context_data) if task.task_context_data else {}
             current_phase = task_context.get("current_phase")
             if current_phase == "AWAITING_PLAN_REVIEW":
                task_context["current_phase"] = "EXECUTING_MILESTONE"
                task_context["current_milestone_index"] = 0
                status_update = models.TaskStatus.EXECUTING_MILESTONE
             elif current_phase == "AWAITING_MILESTONE_REVIEW":
                 current_milestone_idx = task_context.get("current_milestone_index", -1)
                 plan_milestones = task_context.get("plan", {}).get("milestones", [])
                 if 0 <= current_milestone_idx < len(plan_milestones) - 1:
                     task_context["current_milestone_index"] = current_milestone_idx + 1
                     task_context["current_phase"] = "EXECUTING_MILESTONE"
                     status_update = models.TaskStatus.EXECUTING_MILESTONE
                 else:
                     task_context["current_phase"] = "FINALIZING"
                     status_update = models.TaskStatus.APPLIED
             else:
                 raise HTTPException(status_code=400, detail=f"Odyssey task is in an unexpected phase ('{current_phase}') for an approval action.")
             update_data = {
                 "status": status_update,
                 "llm_explanation": f"Admin approved {current_phase}. Proceeding to next step...",
                 "task_context_data": json.dumps(task_context)
             }
             background_tasks.add_task(orchestrator.execute_task, task_id=task.id)
        else:
            update_data = {"status": models.TaskStatus.APPLIED}

        updated_task = crud.update_agent_task(db, db_task=task, task_update_data=update_data)
        notification_service.notify_task_status_change(updated_task)
        return updated_task

    except ValueError as ve:
        logger.warning(f"Approval error for task {task_id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        error_message = f"Failed to approve/process task #{task.id}: {str(e)}"
        logger.error(error_message, exc_info=True)
        crud.update_agent_task(db, db_task=task, task_update_data={"status": models.TaskStatus.ERROR, "error_message": error_message})
        notification_service.notify_task_status_change(task)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)


@router.get("/agent/plugins", response_model=List[Dict[str, str]])
def list_available_plugins(current_user: models.User = Depends(get_current_admin_user)):
    """ADMIN ONLY: Get a list of all loaded agent plugins."""
    plugin_manager = get_plugin_manager()
    return plugin_manager.list_plugins()


@router.get("/agent/permissions", response_model=List[schemas.AgentPermission])
def get_agent_permissions(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    """ADMIN ONLY: Retrieve the list of allowed paths for the Code Modifier agent."""
    return crud.get_permissions(db, limit=1000)


@router.post("/agent/permissions", response_model=schemas.AgentPermission, status_code=status.HTTP_201_CREATED)
def add_agent_permission(permission_in: schemas.AgentPermissionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    """ADMIN ONLY: Add a new allowed path for the Code Modifier agent."""
    existing_perm = crud.get_permission_by_path(db, path=permission_in.path)
    if existing_perm:
        raise HTTPException(status_code=400, detail="Permission path already exists.")
    return crud.create_permission(db, permission_in=permission_in)


@router.delete("/agent/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_permission(permission_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    """ADMIN ONLY: Delete an allowed path for the Code Modifier agent."""
    perm = crud.delete_permission(db, permission_id=permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found.")
    return


@router.get("/settings/notifications", response_model=NotificationSettingsModel)
def get_notification_settings(current_user: models.User = Depends(get_current_admin_user)):
    """ADMIN ONLY: Get the current notification settings from config.yml."""
    return settings.notifications


@router.get("/agent/git/status", response_model=Dict[str, Any])
def get_git_status(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    """ADMIN ONLY: Get the current git status of the codebase."""
    try:
        orchestrator = AgentOrchestrator(db=db)
        if not orchestrator.repo:
            raise HTTPException(status_code=500, detail="Git repository not found on the server.")
        
        return {
            "active_branch": orchestrator.repo.active_branch.name,
            "latest_commit": orchestrator.repo.head.commit.hexsha[:7],
            "uncommitted_changes": orchestrator.repo.is_dirty(untracked_files=True)
        }
    except Exception as e:
        logger.error(f"Failed to get git status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get git status: {e}")
