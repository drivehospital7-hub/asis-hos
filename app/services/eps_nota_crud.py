"""CRUD para eps_nota."""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import EpsNota

logger = logging.getLogger(__name__)


def get_all(db: Session) -> List[EpsNota]:
    """Obtiene todas las relaciones EPS-Nota."""
    return db.query(EpsNota).order_by(EpsNota.id).all()


def get_by_id(db: Session, id: int) -> Optional[EpsNota]:
    """Obtiene relación EPS-Nota por ID."""
    return db.query(EpsNota).filter(EpsNota.id == id).first()


def get_by_nota_hoja(db: Session, id_nota_hoja: int) -> List[EpsNota]:
    """Obtiene relaciones por nota hoja."""
    return db.query(EpsNota).filter(
        EpsNota.id_nota_hoja == id_nota_hoja
    ).all()


def get_by_eps_contratado(db: Session, id_eps_contratado: int) -> List[EpsNota]:
    """Obtiene relaciones por EPS contratada."""
    return db.query(EpsNota).filter(
        EpsNota.id_eps_contratado == id_eps_contratado
    ).all()


def get_by_nota_and_eps(
    db: Session, 
    id_nota_hoja: int, 
    id_eps_contratado: int
) -> Optional[EpsNota]:
    """Obtiene relación por nota hoja y EPS."""
    return db.query(EpsNota).filter(
        and_(
            EpsNota.id_nota_hoja == id_nota_hoja,
            EpsNota.id_eps_contratado == id_eps_contratado
        )
    ).first()


def create(db: Session, id_nota_hoja: int, id_eps_contratado: int) -> EpsNota:
    """Crea una nueva relación EPS-Nota."""
    existing = get_by_nota_and_eps(db, id_nota_hoja, id_eps_contratado)
    if existing:
        raise ValueError(
            f"Ya existe relación entre nota hoja {id_nota_hoja} "
            f"y EPS {id_eps_contratado}"
        )
    
    obj = EpsNota(
        id_nota_hoja=id_nota_hoja,
        id_eps_contratado=id_eps_contratado
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    
    logger.info(f"Creada relación EPS-Nota: hoja={id_nota_hoja}, eps={id_eps_contratado}")
    return obj


def delete(db: Session, id: int) -> bool:
    """Elimina una relación EPS-Nota."""
    obj = get_by_id(db, id)
    if not obj:
        return False
    
    db.delete(obj)
    db.commit()
    
    logger.info(f"Eliminada relación EPS-Nota ID: {id}")
    return True
