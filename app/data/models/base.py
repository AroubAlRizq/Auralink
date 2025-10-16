# app/data/models/base.py
"""
Base imports for models.
All database configuration has been moved to app/data/database/config.py
"""

from app.data.database import Base, engine, SessionLocal, get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db"]

