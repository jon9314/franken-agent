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

# No longer importing directly from plugins
# from app.plugins.odyssey_plugin import ... # REMOVED

router = APIRouter()

# ... (list_all_users_admin, create_new_agent_task, list_agent_tasks_for_admin, get_specific_agent_task_details endpoints are unchanged from Part 6) ...
# (Plugin Listing, Permissions, Settings, Git Status endpoints are also unchanged from Part 6)
# For brevity, only showing the MODIFIED approve endpoint. All other endpoints from Part 6 should be in this file.

@router.post("/agent/tasks/{task_id}/approve", response_model=schemas.AgentTask)
def approve_and_process_agent_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """
    Approves an agent task that is AWAITING_REVIEW. This action signals the task to
    proceed to its next logical phase.

    - For 'code_modifier': Applies code changes and commits to Git.
    - For 'odyssey_agent': Approves the current plan or milestone, transitioning it to the next execution phase.
    - For other plugins: Marks the task as applied.
    """
    task = crud.get_agent_task(db=db, task_id=task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not owned by current admin.")
    
    if task.status != models.TaskStatus.AWAITING_REVIEW:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task is not awaiting review. Current status: {task.status.value}")
    
    orchestrator = AgentOrchestrator(db=db)
    
    try:
        if task.plugin_id == "odyssey_agent":
            # Load the current context to determine the next phase
            task_context = json.loads(task.task_context_data) if task.task_context_data else {}
            current_phase = task_context.get("current_phase")
            
            # This endpoint's job is to transition the state based on approval.
            # The actual work happens when the orchestrator runs the task again.
            if current_phase == "AWAITING_PLAN_REVIEW":
                task_context["current_phase"] = "EXECUTING_MILESTONE"
                task_context["current_milestone_index"] = 0
            elif current_phase == "AWAITING_MILESTONE_REVIEW":
                current_milestone_idx = task_context.get("current_milestone_index", -1)
                plan_milestones = task_context.get("plan", {}).get("milestones", [])
                if 0 <= current_milestone_idx < len(plan_milestones) - 1:
                    task_context["current_milestone_index"] = current_milestone_idx + 1
                    task_context["current_phase"] = "EXECUTING_MILESTONE"
                else:
                    task_context["current_phase"] = "FINALIZING"
            else:
                raise HTTPException(status_code=400, detail=f"Odyssey task is in an unexpected phase ('{current_phase}') for an approval action.")

            update_data = {
                "status": models.TaskStatus.EXECUTING_MILESTONE, # A general "working" status
                "llm_explanation": f"Admin approved {current_phase}. Proceeding to next step...",
                "task_context_data": json.dumps(task_context)
            }
            updated_task = crud.update_agent_task(db, db_task=task, task_update_data=update_data)
            
            # Re-queue the task for the orchestrator to execute the next phase
            background_tasks.add_task(orchestrator.execute_task, task_id=updated_task.id)
            return updated_task

        elif task.plugin_id == "code_modifier":
            commit_hash = orchestrator.apply_and_commit_changes(task, current_user)
            update_data = {"status": models.TaskStatus.APPLIED, "commit_hash": commit_hash}
        
        else: # For other plugins like genealogy_researcher
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
        task_after_error_update_data = {"status": models.TaskStatus.ERROR, "error_message": error_message}
        task_for_error_update = crud.get_agent_task(db, task_id=task_id)
        if task_for_error_update:
            updated_task_on_error = crud.update_agent_task(db, db_task=task_for_error_update, task_update_data=task_after_error_update_data)
            notification_service.notify_task_status_change(updated_task_on_error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

# Make sure the other endpoints from Part 6 are here too:
# /admin/users
# /admin/agent/tasks (create, list, get by id)
# /admin/agent/plugins
# /admin/agent/permissions (get, post, delete)
# /admin/settings/notifications
# /admin/agent/git/status