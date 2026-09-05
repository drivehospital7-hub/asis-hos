"""Reset completo de la base de datos PostgreSQL.

Uso:
    python scripts/reset_db.py          # Pide confirmación
    python scripts/reset_db.py --force  # Sin confirmación

Fases:
    1. DROP TABLE IF EXISTS ... CASCADE (orden inverso de FKs)
    2. Base.metadata.create_all() (5 tablas SQLAlchemy funcionales)
    3. run_migrations() (001)

Requiere:
    - PostgreSQL accesible vía app/utils/db_config.py
    - Variables de entorno cargadas (dotenv)
"""

import argparse
import logging
import sys

# Forzar UTF-8 en stdout (Windows cp1252 no soporta emojis de run_migrations)
sys.stdout.reconfigure(encoding="utf-8")

# Asegurar que el proyecto está en sys.path
sys.path.insert(0, ".")

# ── Imports del proyecto ──────────────────────────────────────────────
import psycopg2

from app.utils.db_config import DB_CONFIG

# ── Configuración logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("reset_db")

# ── Constantes ─────────────────────────────────────────────────────────

# Orden de DROP TABLE (inverso de dependencias FK).
# Las tablas con FKs van primero, las referenciadas después.
# Con CASCADE el orden no es crítico técnicamente, pero es explícito.
DROP_TABLE_ORDER = [
    "eps_nota",          # FK → eps_contratado, nota_hoja
    "notas_tecnicas",    # FK → procedimiento, nota_hoja
    "eps_contratado",    # referenced by eps_nota
    "procedimiento",     # referenced by notas_tecnicas
    "nota_hoja",         # referenced by notas_tecnicas, eps_nota
    "user_areas",        # cleanup (models eliminados)
    "users",             # cleanup (models eliminados)
]

# ── Funciones ──────────────────────────────────────────────────────────

def confirmar_reset() -> bool:
    """Pide confirmación al usuario. Retorna True si confirma."""
    respuesta = input("¿Resetear DB? Esto destruye TODOS los datos. (s/N): ")
    return respuesta.strip().lower() == "s"


def conectar_db():
    """Crea y retorna conexión psycopg2 con autocommit."""
    conn = psycopg2.connect(**DB_CONFIG.psycopg2_dsn)
    conn.autocommit = True
    return conn, conn.cursor()


def dropear_tablas(cursor) -> None:
    """Ejecuta DROP TABLE IF EXISTS ... CASCADE en orden."""
    for table in DROP_TABLE_ORDER:
        logger.info("[DROP] %s", table)
        cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        logger.info("OK")


def crear_tablas_sqlalchemy() -> None:
    """Ejecuta Base.metadata.create_all() para tablas SQLAlchemy."""
    from app.database import Base, _get_engine
    from app import models  # noqa: F401 — asegura que modelos estén registrados

    engine = _get_engine()
    logger.info("[CREATE ALL] Tablas SQLAlchemy")
    Base.metadata.create_all(bind=engine)
    logger.info("OK")


def ejecutar_migraciones() -> None:
    """Ejecuta migraciones SQL vía run_migrations."""
    import run_migrations

    logger.info("[MIGRATE] Ejecutando migraciones...")
    run_migrations.run_migrations()
    logger.info("OK")


def main():
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(
        description="Reset completo de la base de datos PostgreSQL"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ejecuta sin pedir confirmación",
    )
    args = parser.parse_args()

    # ── Confirmación ──────────────────────────────────────────────
    if not args.force:
        if not confirmar_reset():
            logger.info("[ABORT] Operación cancelada por el usuario")
            sys.exit(0)

    try:
        # ── Fase 1: DROP ─────────────────────────────────────────
        conn, cursor = conectar_db()
        dropear_tablas(cursor)
        cursor.close()
        conn.close()

        # ── Fase 2: CREATE ALL ──────────────────────────────────
        crear_tablas_sqlalchemy()

        # ── Fase 3: Migraciones ─────────────────────────────────
        ejecutar_migraciones()

        logger.info("[DONE] DB reset completado exitosamente")
        sys.exit(0)

    except Exception as e:
        logger.exception("[ERROR] Falló el reset de DB: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
