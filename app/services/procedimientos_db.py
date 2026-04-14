"""Servicio de consulta a la base de datos PostgreSQL de procedimientos.

Provee lookups rápidos por EPS + código CUPS.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass
from typing import Optional, List
import logging

from app.utils.db_config import DB_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class Procedimiento:
    """Representa un procedimiento de la DB."""
    id: str  # UUID
    eps: str
    codigo_cups: str
    descripcion: Optional[str]
    tarifa: Optional[float]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _get_connection():
    """Obtiene conexión a PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG.psycopg2_dsn)


def get_procedimiento(eps: str, codigo_cups: str) -> Optional[Procedimiento]:
    """Busca un procedimiento por EPS y código CUPS.
    
    Args:
        eps: Nombre de la EPS (debe coincidir exactamente con la DB)
        codigo_cups: Código CUPS del procedimiento
    
    Returns:
        Procedimiento si existe, None si no se encuentra
    """
    conn = _get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT id, eps, codigo_cups, descripcion, tarifa, created_at, updated_at
        FROM procedimientos
        WHERE eps = %s AND codigo_cups = %s
    """, (eps, codigo_cups))
    
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not row:
        logger.debug("No encontrado: EPS=%s, CUPS=%s", eps, codigo_cups)
        return None
    
    return Procedimiento(
        id=str(row["id"]),
        eps=row["eps"],
        codigo_cups=row["codigo_cups"],
        descripcion=row["descripcion"],
        tarifa=float(row["tarifa"]) if row["tarifa"] else None,
        created_at=str(row["created_at"]) if row["created_at"] else None,
        updated_at=str(row["updated_at"]) if row["updated_at"] else None
    )


def get_all_by_codigo(codigo_cups: str) -> List[Procedimiento]:
    """Busca todas las tarifas para un código CUPS (todas las EPS).
    
    Args:
        codigo_cups: Código CUPS a buscar
    
    Returns:
        Lista de Procedimientos encontrados
    """
    conn = _get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT id, eps, codigo_cups, descripcion, tarifa, created_at, updated_at
        FROM procedimientos
        WHERE codigo_cups = %s
    """, (codigo_cups,))
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [
        Procedimiento(
            id=str(row["id"]),
            eps=row["eps"],
            codigo_cups=row["codigo_cups"],
            descripcion=row["descripcion"],
            tarifa=float(row["tarifa"]) if row["tarifa"] else None,
            created_at=str(row["created_at"]) if row["created_at"] else None,
            updated_at=str(row["updated_at"]) if row["updated_at"] else None
        )
        for row in rows
    ]


def get_all_by_eps(eps: str) -> List[Procedimiento]:
    """Busca todos los procedimientos para una EPS.
    
    Args:
        eps: Nombre de la EPS
    
    Returns:
        Lista de Procedimientos encontrados
    """
    conn = _get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT id, eps, codigo_cups, descripcion, tarifa, created_at, updated_at
        FROM procedimientos
        WHERE eps = %s
        ORDER BY codigo_cups
    """, (eps,))
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [
        Procedimiento(
            id=str(row["id"]),
            eps=row["eps"],
            codigo_cups=row["codigo_cups"],
            descripcion=row["descripcion"],
            tarifa=float(row["tarifa"]) if row["tarifa"] else None,
            created_at=str(row["created_at"]) if row["created_at"] else None,
            updated_at=str(row["updated_at"]) if row["updated_at"] else None
        )
        for row in rows
    ]


def get_eps_disponibles() -> List[str]:
    """Retorna lista de EPS únicas en la DB."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT eps FROM procedimientos ORDER BY eps")
    eps_list = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return eps_list


def verificar_codigo(eps: str, codigo_cups: str) -> tuple[bool, str]:
    """Verifica si un código existe y retorna estado.
    
    Returns:
        Tupla (existe, mensaje)
    """
    proc = get_procedimiento(eps, codigo_cups)
    
    if not proc:
        return False, f"Código {codigo_cups} no encontrado para EPS {eps}"
    
    if proc.descripcion is None:
        return True, f"{codigo_cups} - (sin descripción)"
    
    return True, f"{codigo_cups} - {proc.descripcion}"


def verificar_tarifa(eps: str, codigo_cups: str, tarifa_excel: float, tolerancia: float = 0.01) -> tuple[bool, str]:
    """Verifica si la tarifa del Excel coincide con la DB.
    
    Args:
        eps: EPS del archivo
        codigo_cups: Código del procedimiento
        tarifa_excel: Tarifa que viene en el Excel
        tolerancia: Diferencia aceptable (default 0.01)
    
    Returns:
        Tupla (coincide, mensaje)
    """
    proc = get_procedimiento(eps, codigo_cups)
    
    if not proc:
        return False, f"Código {codigo_cups} no encontrado para EPS {eps}"
    
    if proc.tarifa is None:
        return True, f"{codigo_cups} - Tarifa DB: (no definida)"
    
    diff = abs(proc.tarifa - tarifa_excel)
    
    if diff <= tolerancia:
        return True, f"{codigo_cups} - Excel: {tarifa_excel}, DB: {proc.tarifa} ✓"
    
    return False, f"{codigo_cups} - Excel: {tarifa_excel}, DB: {proc.tarifa} ✗ (diff: {diff})"


# =============================================================================
# Test básico
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== EPS disponibles ===")
    print(get_eps_disponibles())
    
    print("\n=== Ejemplo: Buscar por EPS + código ===")
    proc = get_procedimiento("EMSSANAR_CAPITA", "890201")
    if proc:
        print(f"  {proc.eps} | {proc.codigo_cups} | {proc.descripcion} | {proc.tarifa}")
    else:
        print("  No encontrado")