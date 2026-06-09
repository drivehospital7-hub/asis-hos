"""CRUD para procedimiento."""

import logging
import os
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Procedimiento

logger = logging.getLogger(__name__)

# Patrón que identifica datos generados por fixtures de test
_TEST_DATA_RE = re.compile(r"^PROC V\d+$")

def _is_production_db() -> bool:
    """True si estamos usando la base de producción (sin TEST_DB_NAME)."""
    return not os.getenv("TEST_DB_NAME")


def get_all(db: Session) -> List[Procedimiento]:
    """Obtiene todos los procedimientos."""
    return db.query(Procedimiento).order_by(Procedimiento.procedimiento).all()


def get_by_id(db: Session, id: int) -> Optional[Procedimiento]:
    """Obtiene procedimiento por ID."""
    return db.query(Procedimiento).filter(Procedimiento.id == id).first()


def get_by_cups(db: Session, cups: str) -> Optional[Procedimiento]:
    """Obtiene procedimiento por código CUPS."""
    return db.query(Procedimiento).filter(Procedimiento.cups == cups).first()


def search(db: Session, query: str) -> List[Procedimiento]:
    """Busca procedimientos por nombre (búsqueda parcial)."""
    return db.query(Procedimiento).filter(
        Procedimiento.procedimiento.ilike(f"%{query}%")
    ).order_by(Procedimiento.procedimiento).all()


def create(db: Session, cups: str, procedimiento: str) -> Procedimiento:
    """Crea un nuevo procedimiento."""
    existing = get_by_cups(db, cups)
    if existing:
        raise ValueError(f"Ya existe procedimiento con CUPS: {cups}")
    
    if _is_production_db() and _TEST_DATA_RE.match(procedimiento):
        raise ValueError(
            f"Nombre de procedimiento coincide con patrón de datos de prueba: {procedimiento}"
        )
    
    obj = Procedimiento(
        cups=cups,
        procedimiento=procedimiento
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    
    logger.info("Creado procedimiento: %s | CUPS: %s | ID: %s", procedimiento, cups, obj.id)
    return obj


def update(db: Session, id: int, **kwargs) -> Optional[Procedimiento]:
    """Actualiza un procedimiento."""
    obj = get_by_id(db, id)
    if not obj:
        return None
    
    for key, value in kwargs.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    
    db.commit()
    db.refresh(obj)
    
    logger.info(f"Actualizado procedimiento ID: {id}")
    return obj


def delete(db: Session, id: int) -> bool:
    """Elimina un procedimiento."""
    obj = get_by_id(db, id)
    if not obj:
        return False
    
    db.delete(obj)
    db.commit()
    
    logger.info(f"Eliminado procedimiento ID: {id}")
    return True
