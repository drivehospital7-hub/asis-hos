"""Servicio de operaciones write para la DB de procedimientos (PostgreSQL).

Maneja: insert, update, delete.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass
from typing import Optional
import logging

from app.utils.db_config import DB_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class ProcedimientoInput:
    """Input para crear/actualizar un procedimiento."""
    eps: str
    codigo_cups: str
    descripcion: Optional[str] = None
    tarifa: Optional[float] = None


def _get_connection():
    """Obtiene conexión a PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG.psycopg2_dsn)


def insert_procedimiento(data: ProcedimientoInput) -> tuple[bool, str, Optional[str]]:
    """Inserta un nuevo procedimiento.
    
    Args:
        data: ProcedimientoInput con los datos a insertar
    
    Returns:
        Tupla (éxito, mensaje, id_insertado UUID)
    """
    # Validar required fields
    if not data.eps or not data.eps.strip():
        return False, "EPS es requerida", None
    
    if not data.codigo_cups or not data.codigo_cups.strip():
        return False, "codigo_cups es requerido", None
    
    # Validar tarifa si se provee
    if data.tarifa is not None and data.tarifa <= 0:
        return False, "tarifa debe ser mayor a 0", None
    
    # Check duplicado
    if _existe_procedimiento(data.eps, data.codigo_cups):
        return False, f"Ya existe procedimiento para EPS {data.eps} con código {data.codigo_cups}", None
    
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO procedimientos (eps, codigo_cups, descripcion, tarifa)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            data.eps.strip().upper(),
            data.codigo_cups.strip(),
            data.descripcion,
            data.tarifa
        ))
        
        inserted_id = str(cursor.fetchone()[0])
        conn.commit()
        logger.info("Insertado procedimiento id=%s: %s %s", inserted_id, data.eps, data.codigo_cups)
        return True, "Procedimiento insertado", inserted_id
    
    except psycopg2.Error as e:
        logger.exception("Error insertando procedimiento")
        conn.rollback()
        return False, f"Error al insertar: {str(e)}", None
    
    finally:
        cursor.close()
        conn.close()


def update_procedimiento(procedimiento_id: str, data: ProcedimientoInput) -> tuple[bool, str]:
    """Actualiza un procedimiento existente.
    
    Args:
        procedimiento_id: UUID del procedimiento a actualizar
        data: ProcedimientoInput con los datos a actualizar
    
    Returns:
        Tupla (éxito, mensaje)
    """
    # Validar required fields
    if not data.eps or not data.eps.strip():
        return False, "EPS es requerida"
    
    if not data.codigo_cups or not data.codigo_cups.strip():
        return False, "codigo_cups es requerido"
    
    # Validar tarifa si se provee
    if data.tarifa is not None and data.tarifa <= 0:
        return False, "tarifa debe ser mayor a 0"
    
    # Check que existe
    if not _existe_procedimiento_by_id(procedimiento_id):
        return False, f"Procedimiento con ID {procedimiento_id} no encontrado"
    
    # Check duplicado (otro registro con misma eps+cups)
    existing = _get_procedimiento_by_id(procedimiento_id)
    if existing and (existing.eps != data.eps.strip().upper() or existing.codigo_cups != data.codigo_cups.strip()):
        if _existe_procedimiento(data.eps, data.codigo_cups):
            return False, f"Ya existe procedimiento para EPS {data.eps} con código {data.codigo_cups}"
    
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE procedimientos
            SET eps = %s, codigo_cups = %s, descripcion = %s, tarifa = %s, updated_at = NOW()
            WHERE id = %s
        """, (
            data.eps.strip().upper(),
            data.codigo_cups.strip(),
            data.descripcion,
            data.tarifa,
            procedimiento_id
        ))
        
        conn.commit()
        logger.info("Actualizado procedimiento id=%s", procedimiento_id)
        return True, "Procedimiento actualizado"
    
    except psycopg2.Error as e:
        logger.exception("Error actualizando procedimiento")
        conn.rollback()
        return False, f"Error al actualizar: {str(e)}"
    
    finally:
        cursor.close()
        conn.close()


def delete_procedimiento(procedimiento_id: str) -> tuple[bool, str]:
    """Elimina un procedimiento.
    
    Args:
        procedimiento_id: UUID del procedimiento a eliminar
    
    Returns:
        Tupla (éxito, mensaje)
    """
    # Check que existe
    if not _existe_procedimiento_by_id(procedimiento_id):
        return False, f"Procedimiento con ID {procedimiento_id} no encontrado"
    
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM procedimientos WHERE id = %s", (procedimiento_id,))
        conn.commit()
        logger.info("Eliminado procedimiento id=%s", procedimiento_id)
        return True, "Procedimiento eliminado"
    
    except psycopg2.Error as e:
        logger.exception("Error eliminando procedimiento")
        conn.rollback()
        return False, f"Error al eliminar: {str(e)}"
    
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# Helpers privados
# =============================================================================

def _existe_procedimiento(eps: str, codigo_cups: str) -> bool:
    """Check si existe procedimiento para eps+cups."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM procedimientos
        WHERE eps = %s AND codigo_cups = %s
    """, (eps.strip().upper(), codigo_cups.strip()))
    result = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return result


def _existe_procedimiento_by_id(procedimiento_id: str) -> bool:
    """Check si existe procedimiento por ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM procedimientos WHERE id = %s", (procedimiento_id,))
    result = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return result


def _get_procedimiento_by_id(procedimiento_id: str) -> Optional[ProcedimientoInput]:
    """Obtiene un procedimiento por ID."""
    conn = _get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT eps, codigo_cups, descripcion, tarifa FROM procedimientos WHERE id = %s",
        (procedimiento_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not row:
        return None
    
    return ProcedimientoInput(
        eps=row["eps"],
        codigo_cups=row["codigo_cups"],
        descripcion=row["descripcion"],
        tarifa=float(row["tarifa"]) if row["tarifa"] else None
    )