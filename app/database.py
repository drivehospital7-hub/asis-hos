"""Configuración de base de datos SQLAlchemy (lazy init).

No conecta al cargar el módulo - solo cuando se usa get_db() o SessionLocal.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError

from app.utils.db_config import get_database_config

logger = logging.getLogger(__name__)

Base = declarative_base()

# Lazy: engine y SessionLocal se crean solo cuando se necesitan
_engine = None
_SessionLocal = None


def _get_engine():
    """Crea engine lazily (solo cuando se necesita)."""
    global _engine
    if _engine is None:
        DB_CONFIG = get_database_config()
        _engine = create_engine(
            DB_CONFIG.connection_string,
            poolclass=NullPool,
            echo=False
        )
    return _engine


def _get_session_local():
    """Crea sessionmaker lazily."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Genera sesión de base de datos por request."""
    SessionLocal = _get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verifica si la base de datos está disponible."""
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            return True
    except OperationalError:
        return False


def get_session():
    """Obtiene sesión directa (para scripts como crear_usuarios.py)."""
    return _get_session_local()()


# Backwards compatibility alias - llama lazily
def SessionLocal():
    """Sessionmaker lazy - se crea solo cuando se necesita."""
    return _get_session_local()()