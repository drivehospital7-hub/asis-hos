"""Migración offline explícita: instance/users.json → tabla users.

Uso:
    python scripts/migrate_users_json_to_db.py

Este script NO se ejecuta automáticamente. Debe invocarse como un paso
explícito de deployment/provisioning cuando se necesite importar el backup o
la fuente offline de usuarios.

Qué hace cuando se invoca:
  1. Crea la tabla users si no existe (solo para provisioning explícito).
  2. Hace backup de instance/users.json a instance/users.json.bak.
  3. Upsert por username, sin borrar usuarios que no estén en el JSON.

Después de la migración, la DB es la única fuente runtime de usuarios. Este
script no toca ninguna tabla de negocio ni modifica el JSON de novedades.
"""

import json
import logging
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app.database import Base  # noqa: E402
from app.models import User  # noqa: E402
from app.utils.db_config import get_database_config  # noqa: E402

logger = logging.getLogger(__name__)

USERS_JSON = Path("instance") / "users.json"

load_dotenv()


def migrate_users_json_to_db(users_json: Path = USERS_JSON, session_factory=None) -> dict:
    """Migra usuarios desde un JSON a la tabla users (upsert idempotente).

    Args:
        users_json: ruta al archivo JSON con los usuarios.
        session_factory: factory de sesión (inyectable para tests).
            Default: sessionmaker sobre la DB configurada.

    Returns:
        dict con ``inserted``, ``updated`` y ``backup``.
    """
    users_json = Path(users_json)
    if not users_json.exists():
        raise FileNotFoundError(f"No se encontró {users_json}")

    # 1. Backup del JSON (antes de tocar nada)
    backup_path = users_json.with_name("users.json.bak")
    shutil.copy2(users_json, backup_path)
    logger.info("[BACK] Backup creado: %s", backup_path)

    # 2. Engine + schema
    if session_factory is None:
        db_config = get_database_config()
        engine = create_engine(db_config.connection_string)
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine)

    # 3. Upsert por username. El hash se copia como texto opaco, sin
    # regenerarlo ni incluirlo en logs.
    with open(users_json, "r", encoding="utf-8") as f:
        users = json.load(f)

    inserted = 0
    updated = 0
    db = session_factory()
    try:
        for u in users:
            username = u["username"]
            existing = db.query(User).filter(User.username == username).first()
            if existing is None:
                db.add(
                    User(
                        username=username,
                        password_hash=u["password_hash"],
                        rol=u["rol"],
                        permisos=u.get("permisos", []),
                        primer_nombre=u.get("primer_nombre", ""),
                        segundo_nombre=u.get("segundo_nombre", ""),
                        apellido_1=u.get("apellido_1", ""),
                        apellido_2=u.get("apellido_2", ""),
                    )
                )
                inserted += 1
            else:
                expected = {
                    "password_hash": u["password_hash"],
                    "rol": u["rol"],
                    "permisos": u.get("permisos", []),
                    "primer_nombre": u.get("primer_nombre", ""),
                    "segundo_nombre": u.get("segundo_nombre", ""),
                    "apellido_1": u.get("apellido_1", ""),
                    "apellido_2": u.get("apellido_2", ""),
                }
                current = {
                    "password_hash": existing.password_hash,
                    "rol": existing.rol,
                    "permisos": existing.permisos or [],
                    "primer_nombre": existing.primer_nombre or "",
                    "segundo_nombre": existing.segundo_nombre or "",
                    "apellido_1": existing.apellido_1 or "",
                    "apellido_2": existing.apellido_2 or "",
                }
                if current != expected:
                    existing.password_hash = expected["password_hash"]
                    existing.rol = expected["rol"]
                    existing.permisos = expected["permisos"]
                    existing.primer_nombre = expected["primer_nombre"]
                    existing.segundo_nombre = expected["segundo_nombre"]
                    existing.apellido_1 = expected["apellido_1"]
                    existing.apellido_2 = expected["apellido_2"]
                    updated += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    logger.info(
        "[BACK] Migración completa: %d insertados, %d actualizados",
        inserted,
        updated,
    )
    return {"inserted": inserted, "updated": updated, "backup": str(backup_path)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = migrate_users_json_to_db()
    print(f"Insertados: {result['inserted']}, Actualizados: {result['updated']}")
    print(f"Backup: {result['backup']}")
