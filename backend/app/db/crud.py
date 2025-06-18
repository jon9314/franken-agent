from sqlalchemy.orm import Session
from typing import List, Optional

from app.db import models, schemas
from app.core.security import get_password_hash

# User-related CRUD operations
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """
    Creates a new user in the database.
    This function is now robust and can handle user creation from both
    the public registration form and the admin panel.
    """
    hashed_password = get_password_hash(user.password)

    # Check if a role was provided in the input schema.
    # If not (e.g., from public registration), default to 'user'.
    role = getattr(user, 'role', 'user')

    db_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=role # Use the determined role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> Optional[models.User]:
    user = get_user(db, user_id=user_id)
    if user:
        db.delete(user)
        db.commit()
    return user

# ... (the rest of the file remains the same)
def get_family_tree(db: Session, tree_id: int) -> Optional[models.FamilyTree]:
    return db.query(models.FamilyTree).filter(models.FamilyTree.id == tree_id).first()

def get_family_trees_for_user(db: Session, user_id: int) -> List[models.FamilyTree]:
    return db.query(models.FamilyTree).filter(models.FamilyTree.owner_id == user_id).all()

def create_family_tree(db: Session, file_name: str, user_id: int) -> models.FamilyTree:
    db_tree = models.FamilyTree(file_name=file_name, owner_id=user_id)
    db.add(db_tree)
    db.commit()
    db.refresh(db_tree)
    return db_tree

def add_person_to_tree(db: Session, person_data: schemas.PersonBase, tree_id: int) -> models.Person:
    db_person = models.Person(**person_data.dict(), tree_id=tree_id)
    db.add(db_person)
    db.commit()
    db.refresh(db_person)
    return db_person

# Chat History
def create_chat_history_entry(db: Session, user_id: int, entry: schemas.ChatRequest, response_text: str, model_used: str):
    db_entry = models.ChatHistory(
        user_id=user_id,
        prompt=entry.prompt,
        response=response_text,
        model_used=model_used
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

def get_user_chat_history(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[models.ChatHistory]:
    return db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user_id).order_by(models.ChatHistory.timestamp.desc()).offset(skip).limit(limit).all()

# Agent Tasks
def create_agent_task(db: Session, task_in: schemas.AgentTaskCreate, owner_id: int) -> models.AgentTask:
    db_task = models.AgentTask(**task_in.dict(), owner_id=owner_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_agent_task(db: Session, task_id: int) -> Optional[models.AgentTask]:
    return db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()

def update_agent_task(db: Session, db_task: models.AgentTask, task_update_data: dict) -> models.AgentTask:
    for key, value in task_update_data.items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task

# Agent Permissions
def get_permissions(db: Session, skip: int = 0, limit: int = 100) -> List[models.AgentPermission]:
    return db.query(models.AgentPermission).offset(skip).limit(limit).all()

def get_permission_by_path(db: Session, path: str) -> Optional[models.AgentPermission]:
    return db.query(models.AgentPermission).filter(models.AgentPermission.path == path).first()

def create_permission(db: Session, permission_in: schemas.AgentPermissionCreate) -> models.AgentPermission:
    db_permission = models.AgentPermission(**permission_in.dict())
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)
    return db_permission

def delete_permission(db: Session, permission_id: int) -> Optional[models.AgentPermission]:
    perm = db.query(models.AgentPermission).filter(models.AgentPermission.id == permission_id).first()
    if perm:
        db.delete(perm)
        db.commit()
    return perm
