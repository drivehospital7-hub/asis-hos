"""CRUD para eps_contratado."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import EpsContratado, EpsNota, NotaHoja, NotasTecnicas, Procedimiento

logger = logging.getLogger(__name__)


def get_all(db: Session) -> List[EpsContratado]:
    """Obtiene todas las EPS contratadas."""
    return db.query(EpsContratado).order_by(EpsContratado.eps).all()


def get_by_id(db: Session, id: int) -> Optional[EpsContratado]:
    """Obtiene EPS por ID."""
    return db.query(EpsContratado).filter(EpsContratado.id == id).first()


def get_by_cod_contrato(db: Session, cod_contrato: str) -> Optional[EpsContratado]:
    """Obtiene EPS por código de contrato."""
    return db.query(EpsContratado).filter(EpsContratado.cod_contrato == cod_contrato).first()


def get_by_eps(db: Session, eps: str) -> List[EpsContratado]:
    """Obtiene EPS por nombre (búsqueda parcial)."""
    return db.query(EpsContratado).filter(
        EpsContratado.eps.ilike(f"%{eps}%")
    ).order_by(EpsContratado.eps).all()


def create(db: Session, cod_contrato: str, eps: str, regimen: str = "SUBSIDIADO") -> EpsContratado:
    """Crea una nueva EPS contratada."""
    existing = get_by_cod_contrato(db, cod_contrato)
    if existing:
        raise ValueError(f"Ya existe EPS con código de contrato: {cod_contrato}")
    
    obj = EpsContratado(
        cod_contrato=cod_contrato,
        eps=eps,
        regimen=regimen
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    
    logger.info(f"Creada EPS contratada: {eps} ({cod_contrato})")
    return obj


def update(db: Session, id: int, **kwargs) -> Optional[EpsContratado]:
    """Actualiza una EPS contratada."""
    obj = get_by_id(db, id)
    if not obj:
        return None
    
    for key, value in kwargs.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    
    db.commit()
    db.refresh(obj)
    
    logger.info(f"Actualizada EPS contratada ID: {id}")
    return obj


def get_procedimientos_por_eps(db: Session, eps_id: int) -> List[Dict[str, Any]]:
    """Obtiene procedimientos vinculados a una EPS a través de la cadena completa.

    Recorre: EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento.

    Args:
        db: Sesión de base de datos.
        eps_id: ID de la EPS contratada.

    Returns:
        Lista de dicts con {eps_nota_id, nota_hoja, cups, procedimiento, tarifa}.
        Vacía si no hay resultados.
    """
    results = (
        db.query(EpsContratado, EpsNota, NotaHoja, NotasTecnicas, Procedimiento)
        .join(EpsNota, EpsNota.id_eps_contratado == EpsContratado.id)
        .join(NotaHoja, NotaHoja.id == EpsNota.id_nota_hoja)
        .join(NotasTecnicas, NotasTecnicas.id_nota_hoja == NotaHoja.id)
        .join(Procedimiento, Procedimiento.id == NotasTecnicas.id_procedimiento)
        .filter(EpsContratado.id == eps_id)
        .all()
    )

    return [
        {
            "eps_nota_id": en.id,
            "nota_hoja": nh.nota,
            "cups": proc.cups,
            "procedimiento": proc.procedimiento,
            "tarifa": float(nt.tariff),
        }
        for ec, en, nh, nt, proc in results
    ]


def delete(db: Session, id: int) -> bool:
    """Elimina una EPS которая."""
    obj = get_by_id(db, id)
    if not obj:
        return False
    
    db.delete(obj)
    db.commit()
    
    logger.info(f"Eliminada EPS contratada ID: {id}")
    return True
