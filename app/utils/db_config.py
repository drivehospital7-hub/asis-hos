"""Configuración de base de datos PostgreSQL.

Carga valores desde variables de entorno para conexión.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Configuración de conexión a PostgreSQL."""
    host: str
    port: int
    name: str
    user: str
    password: Optional[str] = None
    
    @property
    def connection_string(self) -> str:
        """Genera connection string para SQLAlchemy."""
        if self.password:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.name}"
    
    @property
    def psycopg2_dsn(self) -> dict:
        """Genera dict para psycopg2."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.name,
            "user": self.user,
            "password": self.password or ""
        }


def get_database_config() -> DatabaseConfig:
    """Lee configuración de variables de entorno."""
    return DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "asis_hos"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD")  # None si no está definido
    )


# Instancia global para usar en toda la app
DB_CONFIG = get_database_config()