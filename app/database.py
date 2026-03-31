"""
Guardian AI — Database Setup
============================
Initializes the SQLAlchemy engine and declarative base.
Defaults to a local SQLite file (guardian.db) but can be easily
configured to use PostgreSQL by setting the DATABASE_URL env var.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# The database connection string.
# Default is 'sqlite:///guardian.db' (creates guardian.db in project root)
# For production (PostgreSQL), set DATABASE_URL=postgresql://user:password@host:port/dbname
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///guardian.db")

# SQLite needs connect_args={'check_same_thread': False} because it's frequently
# accessed across multiple threads in Flask and APScheduler.
# Postgres doesn't need this.
engine_kwargs = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency to yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
