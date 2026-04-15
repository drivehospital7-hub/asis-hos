"""Configuración de base de datos SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from app.utils.db_config import get_database_config

# Crear engine sin pool (para serverless/Functions)
DB_CONFIG = get_database_config()
engine = create_engine(
    DB_CONFIG.connection_string,
    poolclass=NullPool,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Genera sesión de base de datos porrequest."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
