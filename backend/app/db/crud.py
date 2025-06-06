from sqlalchemy.orm import Session
from sqlalchemy import desc # For ordering results
from typing import List, Optional # For type hinting

from app.core.security import get_password_hash
from . import models, schemas # Import local models and schemas

# --- User CRUD ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).order_by(models.User.id).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Chat History CRUD ---
def create_chat_history_entry(db: Session, entry: schemas.ChatRequest, user_id: int, response_text: str, model_used: str) -> models.ChatHistory:
    db_entry = models.ChatHistory(
        user_id=user_id,
        prompt=entry.prompt,
        response=response_text, # Renamed from 'response' to 'response_text' for clarity
        model_used=model_used
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

def get_user_chat_history(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.ChatHistory]:
    return db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user_id).order_by(desc(models.ChatHistory.timestamp)).offset(skip).limit(limit).all()

# --- AgentTask CRUD ---
def get_agent_task(db: Session, task_id: int) -> Optional[models.AgentTask]:
    return db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()

def get_agent_tasks_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 20) -> List[models.AgentTask]: # Default limit 20 for admin view
    return db.query(models.AgentTask).filter(models.AgentTask.owner_id == owner_id).order_by(desc(models.AgentTask.created_at)).offset(skip).limit(limit).all()

def create_agent_task(db: Session, task_in: schemas.AgentTaskCreate, owner_id: int) -> models.AgentTask:
    db_task = models.AgentTask(
        prompt=task_in.prompt,
        plugin_id=task_in.plugin_id,
        target_files=task_in.target_files,
        target_tree_id=task_in.target_tree_id,
        target_person_id=task_in.target_person_id,
        owner_id=owner_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_agent_task(db: Session, db_task: models.AgentTask, task_update_data: dict) -> models.AgentTask: # Use dict for flexibility
    for field, value in task_update_data.items():
        if hasattr(db_task, field):
            setattr(db_task, field, value)
    db.add(db_task) # Add to session to mark as dirty
    db.commit()
    db.refresh(db_task)
    return db_task

# --- AgentPermission CRUD ---
def get_permission_by_path(db: Session, path: str) -> Optional[models.AgentPermission]:
    return db.query(models.AgentPermission).filter(models.AgentPermission.path == path).first()

def get_permissions(db: Session, skip: int = 0, limit: int = 100) -> List[models.AgentPermission]:
    return db.query(models.AgentPermission).order_by(models.AgentPermission.path).offset(skip).limit(limit).all()

def create_permission(db: Session, permission_in: schemas.AgentPermissionCreate) -> models.AgentPermission:
    db_permission = models.AgentPermission(**permission_in.dict())
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)
    return db_permission

def delete_permission(db: Session, permission_id: int) -> Optional[models.AgentPermission]:
    db_permission = db.query(models.AgentPermission).filter(models.AgentPermission.id == permission_id).first()
    if db_permission:
        db.delete(db_permission)
        db.commit()
    return db_permission # Returns the deleted object or None if not found

# --- Genealogy CRUD ---
def create_family_tree(db: Session, file_name: str, owner_id: int) -> models.FamilyTree:
    db_tree = models.FamilyTree(file_name=file_name, owner_id=owner_id)
    db.add(db_tree)
    db.commit()
    db.refresh(db_tree)
    return db_tree

def get_family_trees_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[models.FamilyTree]:
    return db.query(models.FamilyTree).filter(models.FamilyTree.owner_id == owner_id).order_by(desc(models.FamilyTree.created_at)).offset(skip).limit(limit).all()

def get_family_tree_with_details(db: Session, tree_id: int, owner_id: int) -> Optional[models.FamilyTree]:
    """Fetches a family tree ensuring it belongs to the owner, and eagerly loads persons and families."""
    # Eager loading can be complex with nested structures.
    # For very large trees, consider paginating persons/families separately.
    return db.query(models.FamilyTree).filter(
        models.FamilyTree.id == tree_id, 
        models.FamilyTree.owner_id == owner_id
    ).first()
    # For explicit eager loading (might be default depending on relationship config):
    # from sqlalchemy.orm import joinedload, selectinload
    # return db.query(models.FamilyTree).options(
    #     selectinload(models.FamilyTree.persons),
    #     selectinload(models.FamilyTree.families).selectinload(models.Family.husband),
    #     selectinload(models.FamilyTree.families).selectinload(models.Family.wife),
    #     selectinload(models.FamilyTree.families).selectinload(models.Family.children)
    # ).filter(models.FamilyTree.id == tree_id, models.FamilyTree.owner_id == owner_id).first()


def get_person_by_id(db: Session, person_id: int) -> Optional[models.Person]:
    return db.query(models.Person).filter(models.Person.id == person_id).first()

def get_research_finding_by_id(db: Session, finding_id: int) -> Optional[models.ResearchFinding]:
    return db.query(models.ResearchFinding).filter(models.ResearchFinding.id == finding_id).first()

def create_research_finding(db: Session, finding_in: schemas.ResearchFindingCreate) -> models.ResearchFinding:
    db_finding = models.ResearchFinding(**finding_in.dict())
    db.add(db_finding)
    db.commit()
    db.refresh(db_finding)
    return db_finding

def update_research_finding(db: Session, db_finding: models.ResearchFinding, finding_update_data: dict) -> models.ResearchFinding:
    for field, value in finding_update_data.items():
        if hasattr(db_finding, field):
            setattr(db_finding, field, value)
    db.add(db_finding)
    db.commit()
    db.refresh(db_finding)
    return db_finding

def get_research_findings_for_person(db: Session, person_id: int, skip: int = 0, limit: int = 100) -> List[models.ResearchFinding]:
    return db.query(models.ResearchFinding).filter(
        models.ResearchFinding.person_id == person_id
    ).order_by(desc(models.ResearchFinding.created_at)).offset(skip).limit(limit).all()

def get_all_unverified_research_findings(db: Session, skip: int = 0, limit: int = 100) -> List[models.ResearchFinding]:
    """Gets all research findings across all users/trees that are UNVERIFIED for admin review."""
    return db.query(models.ResearchFinding).filter(
        models.ResearchFinding.status == models.FindingStatus.UNVERIFIED
    ).order_by(desc(models.ResearchFinding.created_at)).offset(skip).limit(limit).all()