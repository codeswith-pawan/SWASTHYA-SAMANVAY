"""
Database convenience module for SWASTHYA SAMANVAY.
Exposes database engine, session dependencies, Base declarative class,
and init_database runner.
"""

from src.database.db_manager import (
    get_engine,
    get_session_factory,
    get_db_session,
    is_postgres,
    is_production,
    check_db_health,
)
from src.database.database import Base as SqliteBase, engine as sqlite_engine, get_db
from src.database.pg_models import PgBase
from src.database.init_db import init_database, seed_baseline_reference_data

# Primary Base for all relational models
Base = PgBase
engine = sqlite_engine
SessionLocal = get_session_factory()

__all__ = [
    "Base",
    "PgBase",
    "SqliteBase",
    "engine",
    "SessionLocal",
    "get_engine",
    "get_db",
    "get_db_session",
    "get_session_factory",
    "init_database",
    "seed_baseline_reference_data",
    "is_postgres",
    "is_production",
    "check_db_health",
]
