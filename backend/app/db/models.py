from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as DBEnum, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .database import Base

# --- User Model ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    
    tasks = relationship("AgentTask", back_populates="owner")
    chat_history = relationship("ChatHistory", back_populates="owner")
    family_trees = relationship("FamilyTree", back_populates="owner")
    reviewed_findings = relationship("ResearchFinding", foreign_keys="[ResearchFinding.reviewed_by_id]", back_populates="reviewer")


# --- Chat History Model ---
class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model_used = Column(String, nullable=False)
    owner = relationship("User", back_populates="chat_history")


# --- Agent Task Related Enums ---
class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"               # <-- NEW: Odyssey is generating a plan
    ANALYZING = "ANALYZING"
    TESTING = "TESTING"
    AWAITING_REVIEW = "AWAITING_REVIEW" # Generic review state
    EXECUTING_MILESTONE = "EXECUTING_MILESTONE" # <-- NEW: Odyssey is working on a milestone
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"

class TestStatus(str, enum.Enum):
    NOT_RUN = "NOT_RUN"
    PASS = "PASS"
    FAIL = "FAIL"

# --- Agent Task Model ---
class AgentTask(Base):
    __tablename__ = "agent_tasks"
    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    plugin_id = Column(String, nullable=False, default="code_modifier")
    target_files = Column(Text, nullable=True)
    status = Column(DBEnum(TaskStatus, name="task_status_enum_v4"), nullable=False, default=TaskStatus.PENDING)
    llm_explanation = Column(Text, nullable=True)
    proposed_diff = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    commit_hash = Column(String, nullable=True)
    test_status = Column(DBEnum(TestStatus, name="test_status_enum_v4"), nullable=False, default=TestStatus.NOT_RUN)
    test_results = Column(Text, nullable=True)
    target_tree_id = Column(Integer, ForeignKey("genealogy_family_trees.id"), nullable=True)
    target_person_id = Column(Integer, ForeignKey("genealogy_persons.id"), nullable=True)
    
    # --- NEW field for Odyssey Plugin state ---
    task_context_data = Column(Text, nullable=True) # Stores JSON string for plan, current milestone, etc.
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="tasks")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# ... (AgentPermission, FamilyTree, Person, Family, ResearchFinding models remain the same) ...