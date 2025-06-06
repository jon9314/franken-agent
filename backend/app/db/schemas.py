from pydantic import BaseModel, EmailStr, Field, HttpUrl # Added HttpUrl
from typing import Optional, List
from datetime import datetime
# Import enums from models.py where they are now defined with Python's enum
from .models import TaskStatus, TestStatus, FindingStatus 

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: str = Field("user", pattern="^(user|admin)$")
class UserInDBBase(UserBase):
    id: int
    role: str
    class Config: from_attributes = True 
class UserPublic(UserInDBBase): pass
class User(UserInDBBase): pass

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

class AgentTaskCreate(AgentTaskBase): # This is used for request body on task creation
    plugin_id: str = Field(..., description="ID of the plugin to use for this task (e.g., 'code_modifier', 'odyssey_agent')")
    target_tree_id: Optional[int] = Field(None, description="For genealogy_researcher: DB ID of the FamilyTree")
    target_person_id: Optional[int] = Field(None, description="For genealogy_researcher: DB ID of the Person")

class AgentTask(AgentTaskBase): # This is the main response model for an AgentTask
    id: int
    owner_id: int
    plugin_id: str
    status: TaskStatus # Use the enum from models
    llm_explanation: Optional[str] = None
    proposed_diff: Optional[str] = None # For code_modifier
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None # For code_modifier
    created_at: datetime
    updated_at: Optional[datetime] = None
    test_status: TestStatus # Use the enum from models
    test_results: Optional[str] = None # For code_modifier
    target_tree_id: Optional[int] = None
    target_person_id: Optional[int] = None
    
    # --- NEW field for Odyssey Plugin state ---
    task_context_data: Optional[str] = Field(None, description="JSON string storing complex state for plugins like Odyssey Agent (e.g., plan, current milestone).")
    
    class Config: from_attributes = True

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
    gedcom_id: str = Field(..., example="@I1@")
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Smith")
    sex: Optional[str] = Field(None, example="M", max_length=10)
    birth_date: Optional[str] = Field(None, example="1 JAN 1900")
    birth_place: Optional[str] = Field(None, example="New York, USA") # Changed to str from Text
    death_date: Optional[str] = Field(None, example="15 MAR 1980")
    death_place: Optional[str] = Field(None, example="Los Angeles, USA") # Changed to str from Text
class Person(PersonBase):
    id: int
    tree_id: int
    class Config: from_attributes = True

class FamilyBase(BaseModel):
    gedcom_id: str = Field(..., example="@F1@")
class Family(FamilyBase):
    id: int
    tree_id: int
    husband: Optional[Person] = None
    wife: Optional[Person] = None
    children: List[Person] = []
    class Config: from_attributes = True

class FamilyTreeBase(BaseModel):
    file_name: str = Field(..., example="smith_family.ged")
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
    data_field: str = Field(..., example="birth_date")
    original_value: Optional[str] = None
    suggested_value: Optional[str] = None
    source_name: str = Field(..., example="FindAGrave.com")
    source_url: Optional[HttpUrl] = None # Use HttpUrl for validation
    citation_text: str
    confidence_score: Optional[int] = Field(None, ge=0, le=100)
    llm_reasoning: Optional[str] = None
class ResearchFindingCreate(ResearchFindingBase): # Used internally by plugins to create findings
    person_id: int
    agent_task_id: int
class ResearchFinding(ResearchFindingBase): # For API responses
    id: int
    person_id: int
    agent_task_id: int
    status: FindingStatus # Use the enum from models
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_id: Optional[int] = None
    class Config: from_attributes = True

class GitStatus(BaseModel): # For Admin endpoint
    active_branch: str
    latest_commit: Optional[str] = None
    uncommitted_changes: bool