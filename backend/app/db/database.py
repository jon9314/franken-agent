from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings # To get the DATABASE_URL

# The `connect_args` are needed only for SQLite to allow multi-threaded access.
# For other databases like PostgreSQL, this might not be necessary or different.
engine_args = {}
if settings.DATABASE_URL and settings.DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    str(settings.DATABASE_URL), **engine_args # Ensure DATABASE_URL is string
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session (moved to core.dependencies.py)
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()