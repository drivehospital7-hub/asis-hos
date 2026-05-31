"""Servicio para vincular procedimiento a EPS en transacción atómica.

Crea EpsNota + NotasTecnicas en un solo commit, sin reutilizar
los CRUDs existentes que hacen commit individual.
"""

import logging
from decimal import Decimal
from typing import Dict, Tuple

from sqlalchemy.orm import Session

from app.models import EpsContratado, EpsNota, NotaHoja, NotasTecnicas, Procedimiento

logger = logging.getLogger(__name__)


def ejecutar(
    db: Session,
    eps_id: int,
    id_nota_hoja: int,
    id_procedimiento: int,
    tarifa: float,
) -> Tuple[EpsNota, NotasTecnicas]:
    """Vincula un procedimiento a una EPS en una transacción atómica.

    Crea EpsNota y NotasTecnicas en un solo commit. Si algo falla,
    hace rollback completo.

    Args:
        db: Sesión de base de datos.
        eps_id: ID de EpsContratado.
        id_nota_hoja: ID de NotaHoja.
        id_procedimiento: ID de Procedimiento.
        tarifa: Valor de la tarifa (se mapea a tariff en DB).

    Returns:
        Tupla (EpsNota, NotasTecnicas) creados.

    Raises:
        ValueError: Si alguna entidad no existe, hay duplicado, o tarifa inválida.
    """
    # ─── Validaciones ─────────────────────────────────────────────────

    if tarifa is None:
        raise ValueError("Tarifa es requerida")

    try:
        tarifa_val = float(tarifa)
    except (TypeError, ValueError):
        raise ValueError("Tarifa inválida")

    if tarifa_val <= 0:
        raise ValueError("Tarifa inválida")

    eps = db.query(EpsContratado).filter(EpsContratado.id == eps_id).first()
    if not eps:
        raise ValueError(f"No existe EPS con id: {eps_id}")

    nh = db.query(NotaHoja).filter(NotaHoja.id == id_nota_hoja).first()
    if not nh:
        raise ValueError("NotaHoja no encontrada")

    proc = db.query(Procedimiento).filter(Procedimiento.id == id_procedimiento).first()
    if not proc:
        raise ValueError("Procedimiento no encontrado")

    # Verificar duplicado en EpsNota
    existing_en = (
        db.query(EpsNota)
        .filter(
            EpsNota.id_nota_hoja == id_nota_hoja,
            EpsNota.id_eps_contratado == eps_id,
        )
        .first()
    )
    if existing_en:
        raise ValueError("Combinación ya existe")

    # ─── Transacción ──────────────────────────────────────────────────

    try:
        eps_nota = EpsNota(
            id_nota_hoja=id_nota_hoja,
            id_eps_contratado=eps_id,
        )
        db.add(eps_nota)
        db.flush()

        nt = NotasTecnicas(
            id_procedimiento=id_procedimiento,
            id_nota_hoja=id_nota_hoja,
            tariff=tarifa_val,
        )
        db.add(nt)
        db.flush()

        db.commit()
        db.refresh(eps_nota)
        db.refresh(nt)

        logger.info(
            "Vinculado procedimiento %s a EPS %s mediante NotaHoja %s (tarifa=%s)",
            id_procedimiento, eps_id, id_nota_hoja, tarifa_val,
        )
        return eps_nota, nt

    except Exception:
        db.rollback()
        logger.exception("Error al vincular procedimiento a EPS")
        raise
