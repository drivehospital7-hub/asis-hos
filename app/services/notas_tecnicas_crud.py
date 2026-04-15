"""CRUD para notas_tecnicas."""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import NotasTecnicas

logger = logging.getLogger(__name__)


def get_all(db: Session) -> List[NotasTecnicas]:
    """Obtiene todas las notas técnicas."""
    return db.query(NotasTecnicas).order_by(NotasTecnicas.id).all()


def get_by_id(db: Session, id: int) -> Optional[NotasTecnicas]:
    """Obtiene nota técnica por ID."""
    return db.query(NotasTecnicas).filter(NotasTecnicas.id == id).first()


def get_by_procedimiento(db: Session, id_procedimiento: int) -> List[NotasTecnicas]:
    """Obtiene notas técnicas por procedimiento."""
    return db.query(NotasTecnicas).filter(
        NotasTecnicas.id_procedimiento == id_procedimiento
    ).all()


def get_by_nota_hoja(db: Session, id_nota_hoja: int) -> List[NotasTecnicas]:
    """Obtiene notas técnicas por nota hoja."""
    return db.query(NotasTecnicas).filter(
        NotasTecnicas.id_nota_hoja == id_nota_hoja
    ).all()


def get_by_procedimiento_and_nota(
    db: Session, 
    id_procedimiento: int, 
    id_nota_hoja: int
) -> Optional[NotasTecnicas]:
    """Obtiene nota técnica por procedimiento y nota hoja."""
    return db.query(NotasTecnicas).filter(
        and_(
            NotasTecnicas.id_procedimiento == id_procedimiento,
            NotasTecnicas.id_nota_hoja == id_nota_hoja
        )
    ).first()


def create(
    db: Session, 
    id_procedimiento: int, 
    id_nota_hoja: int, 
    tarifa: float
) -> NotasTecnicas:
    """Crea una nueva nota técnica."""
    existing = get_by_procedimiento_and_nota(db, id_procedimiento, id_nota_hoja)
    if existing:
        raise ValueError(
            f"Ya existe nota técnica para procedimiento {id_procedimiento} "
            f"y nota hoja {id_nota_hoja}"
        )
    
    obj = NotasTecnicas(
        id_procedimiento=id_procedimiento,
        id_nota_hoja=id_nota_hoja,
        tarifa=tarifa
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    
    logger.info(f"Creada nota técnica: proc={id_procedimiento}, hoja={id_nota_hoja}, tarifa={tarifa}")
    return obj


def update(db: Session, id: int, **kwargs) -> Optional[NotasTecnicas]:
    """Actualiza una nota técnica."""
    obj = get_by_id(db, id)
    if not obj:
        return None
    
    for key, value in kwargs.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    
    db.commit()
    db.refresh(obj)
    
    logger.info(f"Actualizada nota técnica ID: {id}")
    return obj


def delete(db: Session, id: int) -> bool:
    """Elimina una nota técnica."""
    obj = get_by_id(db, id)
    if not obj:
        return False
    
    db.delete(obj)
    db.commit()
    
    logger.info(f"Eliminada nota técnica ID: {id}")
    return True
