"""CRUD para nota_hoja."""

import logging
import os
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import NotaHoja

logger = logging.getLogger(__name__)

# Patrón que identifica datos generados por fixtures de test
_TEST_DATA_RE = re.compile(r"^NOTA V\d+$")

def _is_production_db() -> bool:
    """True si estamos usando la base de producción (sin TEST_DB_NAME)."""
    return not os.getenv("TEST_DB_NAME")


def get_all(db: Session) -> List[NotaHoja]:
    """Obtiene todas las notas hojas."""
    return db.query(NotaHoja).order_by(NotaHoja.nota).all()


def get_by_id(db: Session, id: int) -> Optional[NotaHoja]:
    """Obtiene nota hoja por ID."""
    return db.query(NotaHoja).filter(NotaHoja.id == id).first()


def get_by_nota(db: Session, nota: str) -> Optional[NotaHoja]:
    """Obtiene nota hoja por nombre."""
    return db.query(NotaHoja).filter(NotaHoja.nota == nota).first()


def search(db: Session, query: str) -> List[NotaHoja]:
    """Busca notas hojas por nombre (búsqueda parcial)."""
    return db.query(NotaHoja).filter(
        NotaHoja.nota.ilike(f"%{query}%")
    ).order_by(NotaHoja.nota).all()


def create(db: Session, nota: str) -> NotaHoja:
    """Crea una nueva nota hoja."""
    existing = get_by_nota(db, nota)
    if existing:
        raise ValueError(f"Ya existe nota hoja: {nota}")
    
    if _is_production_db() and _TEST_DATA_RE.match(nota):
        raise ValueError(
            f"Nombre de nota coincide con patrón de datos de prueba: {nota}"
        )
    
    obj = NotaHoja(nota=nota)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    
    logger.info("Creada nota hoja: %s | ID: %s", nota, obj.id)
    return obj


def update(db: Session, id: int, **kwargs) -> Optional[NotaHoja]:
    """Actualiza una nota hoja."""
    obj = get_by_id(db, id)
    if not obj:
        return None
    
    for key, value in kwargs.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    
    db.commit()
    db.refresh(obj)
    
    logger.info(f"Actualizada nota hoja ID: {id}")
    return obj


def delete(db: Session, id: int) -> bool:
    """Elimina una nota hoja y sus dependencias (eps_nota, notas_tecnicas)."""
    obj = get_by_id(db, id)
    if not obj:
        return False
    
    from app.models import EpsNota, NotasTecnicas
    
    # Eliminar dependencias primero (FK no permiten NULL ni ON DELETE CASCADE)
    db.query(EpsNota).filter(EpsNota.id_nota_hoja == id).delete()
    db.query(NotasTecnicas).filter(NotasTecnicas.id_nota_hoja == id).delete()
    
    db.delete(obj)
    db.commit()
    
    logger.info(f"Eliminada nota hoja ID: {id} con dependencias")
    return True
