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
# --- AgentPermission Model ---
class AgentPermission(Base):
    __tablename__ = "agent_permissions"
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=False, unique=True, index=True)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Genealogy Models ---

# Association Table for the many-to-many relationship between Family and Children (Person)
family_child_association = Table(
    'family_child_association',
    Base.metadata,
    Column('family_id', Integer, ForeignKey('genealogy_families.id'), primary_key=True),
    Column('person_id', Integer, ForeignKey('genealogy_persons.id'), primary_key=True)
)

class FamilyTree(Base):
    __tablename__ = "genealogy_family_trees"
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="family_trees")
    persons = relationship("Person", back_populates="tree", cascade="all, delete-orphan")
    families = relationship("Family", back_populates="tree", cascade="all, delete-orphan")

class Person(Base):
    __tablename__ = "genealogy_persons"
    id = Column(Integer, primary_key=True, index=True)
    gedcom_id = Column(String, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    sex = Column(String(1), nullable=True)
    birth_date = Column(String, nullable=True)
    birth_place = Column(String, nullable=True)
    death_date = Column(String, nullable=True)
    death_place = Column(String, nullable=True)
    
    tree_id = Column(Integer, ForeignKey("genealogy_family_trees.id"), nullable=False)
    tree = relationship("FamilyTree", back_populates="persons")
    
    # Relationship to research findings
    findings = relationship("ResearchFinding", back_populates="person", cascade="all, delete-orphan")

class Family(Base):
    __tablename__ = "genealogy_families"
    id = Column(Integer, primary_key=True, index=True)
    gedcom_id = Column(String, index=True)
    
    tree_id = Column(Integer, ForeignKey("genealogy_family_trees.id"), nullable=False)
    tree = relationship("FamilyTree", back_populates="families")
    
    husband_id = Column(Integer, ForeignKey("genealogy_persons.id"), nullable=True)
    wife_id = Column(Integer, ForeignKey("genealogy_persons.id"), nullable=True)
    
    husband = relationship("Person", foreign_keys=[husband_id])
    wife = relationship("Person", foreign_keys=[wife_id])
    
    children = relationship("Person", secondary=family_child_association)

# Enum for the status of a research finding
class FindingStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class ResearchFinding(Base):
    __tablename__ = "genealogy_research_findings"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("genealogy_persons.id"), nullable=False)
    agent_task_id = Column(Integer, ForeignKey("agent_tasks.id"), nullable=False)
    
    data_field = Column(String, nullable=False)
    original_value = Column(String, nullable=True)
    suggested_value = Column(String, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    llm_reasoning = Column(Text, nullable=True)
    source_name = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    citation_text = Column(Text, nullable=True)
    
    status = Column(DBEnum(FindingStatus, name="finding_status_enum"), nullable=False, default=FindingStatus.UNVERIFIED)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    person = relationship("Person", back_populates="findings")
    reviewer = relationship("User", foreign_keys=[reviewed_by_id], back_populates="reviewed_findings")
