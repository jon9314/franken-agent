from __future__ import annotations # MUST be at the top of the file
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
# Import enums directly from models.py where they are defined
from . import models

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    # The 'role' is now defined in the more specific class below

class UserInDBBase(UserBase):
    id: int
    role: str
    class Config: from_attributes = True 

class UserPublic(UserInDBBase): pass

class User(UserInDBBase):
    family_trees: List[FamilyTreeSimple] = []
    class Config: from_attributes = True

# --- This is the new class we are adding ---
class UserCreateWithRole(UserCreate):
    role: str = "user"

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    email: Optional[EmailStr] = None

# --- Chat & Inference Schemas ---
class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
class ChatResponse(BaseModel):
    response: str
    model_used: str
class ChatHistoryEntry(BaseModel):
    id: int
    timestamp: datetime
    prompt: str
    response: str
    model_used: str
    class Config: from_attributes = True

# --- Model Info Schemas (for Ollama models) ---
class ModelInfo(BaseModel):
    server_name: str
    model_name: str

# --- Agent Schemas ---
class AgentTaskBase(BaseModel):
    prompt: str
    target_files: Optional[str] = Field(None, description="Comma-separated paths for code_modifier plugin")
class AgentTaskCreate(AgentTaskBase):
    plugin_id: str
    target_tree_id: Optional[int] = None
    target_person_id: Optional[int] = None
class AgentTask(AgentTaskBase):
    id: int
    owner_id: int
    plugin_id: str
    status: models.TaskStatus # Use the direct reference
    llm_explanation: Optional[str] = None
    proposed_diff: Optional[str] = None
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    test_status: models.TestStatus # Use the direct reference
    test_results: Optional[str] = None
    target_tree_id: Optional[int] = None
    target_person_id: Optional[int] = None
    task_context_data: Optional[str] = None
    class Config: from_attributes = True

# --- Agent Permission Schemas ---
class AgentPermissionBase(BaseModel):
    path: str
    comment: Optional[str] = None
class AgentPermissionCreate(AgentPermissionBase): pass
class AgentPermission(AgentPermissionBase):
    id: int
    created_at: datetime
    class Config: from_attributes = True

# --- Genealogy Schemas ---
class PersonBase(BaseModel):
    gedcom_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    sex: Optional[str] = None
    birth_date: Optional[str] = None
    birth_place: Optional[str] = None
    death_date: Optional[str] = None
    death_place: Optional[str] = None
class Person(PersonBase):
    id: int
    tree_id: int
    findings: List['ResearchFinding'] = [] # Use forward reference as a string
    class Config: from_attributes = True

class FamilyBase(BaseModel):
    gedcom_id: str
class Family(FamilyBase):
    id: int
    tree_id: int
    husband: Optional[Person] = None
    wife: Optional[Person] = None
    children: List[Person] = []
    class Config: from_attributes = True

class FamilyTreeBase(BaseModel):
    file_name: str
class FamilyTreeSimple(FamilyTreeBase):
    id: int
    owner_id: int
    created_at: datetime
    class Config: from_attributes = True
class FamilyTree(FamilyTreeSimple):
    persons: List[Person] = []
    families: List[Family] = []
    class Config: from_attributes = True

class ResearchFindingBase(BaseModel):
    data_field: str
    original_value: Optional[str] = None
    suggested_value: Optional[str] = None
    source_name: str
    source_url: Optional[HttpUrl] = None
    citation_text: str
    confidence_score: Optional[int] = Field(None, ge=0, le=100)
    llm_reasoning: Optional[str] = None
class ResearchFindingCreate(ResearchFindingBase):
    person_id: int
    agent_task_id: int
class ResearchFinding(ResearchFindingBase):
    id: int
    person_id: int
    agent_task_id: int
    status: models.FindingStatus # Use the direct reference
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_id: Optional[int] = None
    class Config: from_attributes = True

# This resolves the forward references (the type hints that are strings)
User.update_forward_refs()
Person.update_forward_refs()
