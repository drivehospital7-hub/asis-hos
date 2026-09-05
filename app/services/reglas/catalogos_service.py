"""CRUD operations for the catalogos table (JSONB catalogs).

All functions accept a SQLAlchemy Session as first argument.
Returns dicts following the canonical envelope data format.
"""

from __future__ import annotations

import json as json_lib
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS catalogos (
        id SERIAL PRIMARY KEY,
        key VARCHAR(200) NOT NULL UNIQUE,
        value JSONB NOT NULL DEFAULT '[]'::jsonb,
        dominio TEXT,
        descripcion TEXT,
        updated_at TIMESTAMPTZ DEFAULT now()
    )
"""


def _ensure_table(db) -> None:
    """Create the catalogos table if it doesn't exist (idempotent)."""
    try:
        db.execute(text(_CREATE_TABLE_SQL))
        db.commit()
    except Exception:
        db.rollback()


def list_catalogos(db) -> list[dict]:
    """List all catalogs with rule reference count.

    Returns a list of dicts with key, descripcion, dominio, value, value_count,
    regla_count, and updated_at, ordered by key.
    """
    _ensure_table(db)
    rows = db.execute(text("""
        SELECT
            c.key,
            c.descripcion,
            c.dominio,
            c.value,
            c.updated_at,
            COALESCE(jsonb_array_length(c.value), 0) AS value_count,
            COALESCE((
                SELECT COUNT(DISTINCT r.id)
                FROM condiciones cd
                JOIN reglas r ON r.id = cd.regla_id
                WHERE cd.operador = 'cat_in'
                  AND cd.valor_esperado #>> '{}' = c.key
            ), 0) AS regla_count
        FROM catalogos c
        ORDER BY c.key
    """)).fetchall()

    result = []
    for row in rows:
        mapping = row._mapping
        val = mapping["value"]
        result.append({
            "key": mapping["key"],
            "descripcion": mapping["descripcion"],
            "dominio": mapping["dominio"],
            "value": val if isinstance(val, list) else [],
            "value_count": mapping["value_count"],
            "regla_count": mapping["regla_count"],
            "updated_at": mapping["updated_at"],
        })
    return result


def get_catalogo(db, key: str) -> dict | None:
    """Get a single catalog by key.

    Returns dict with key, values (list), value_count, descripcion, dominio,
    updated_at, or None if not found.
    """
    row = db.execute(
        text("""
            SELECT key, value, descripcion, dominio, updated_at
            FROM catalogos
            WHERE key = :key
        """),
        {"key": key},
    ).fetchone()

    if row is None:
        return None

    mapping = row._mapping
    val = mapping["value"]
    if not isinstance(val, list):
        val = []
    return {
        "key": mapping["key"],
        "values": val,
        "value_count": len(val),
        "descripcion": mapping["descripcion"],
        "dominio": mapping["dominio"],
        "updated_at": mapping["updated_at"],
    }


def create_catalogo(db, data: dict) -> dict:
    """Create a new catalog entry.

    Args:
        db: SQLAlchemy Session
        data: dict with 'key' (required), 'value' (optional list, default []),
              'descripcion' (optional), 'dominio' (optional)

    Returns:
        dict: Created catalog row

    Raises:
        ValueError: If key is missing, value is not a list, or key already exists
    """
    key = data.get("key")
    if not key:
        raise ValueError("Campo requerido: key")

    value = data.get("value", [])
    if not isinstance(value, list):
        raise ValueError("El campo 'value' debe ser un array JSON")

    descripcion = data.get("descripcion")
    dominio = data.get("dominio")

    try:
        row = db.execute(
            text("""
                INSERT INTO catalogos (key, value, descripcion, dominio)
                VALUES (:key, CAST(:value AS jsonb), :descripcion, :dominio)
                RETURNING key, value, descripcion, dominio, updated_at
            """),
            {
                "key": key,
                "value": json_lib.dumps(value),
                "descripcion": descripcion,
                "dominio": dominio,
            },
        ).fetchone()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"El key '{key}' ya existe en catalogos")

    mapping = row._mapping
    val = mapping["value"]
    if not isinstance(val, list):
        val = []
    return {
        "key": mapping["key"],
        "values": val,
        "value_count": len(val),
        "descripcion": mapping["descripcion"],
        "dominio": mapping["dominio"],
        "updated_at": mapping["updated_at"],
    }


def update_catalogo(db, key: str, data: dict) -> dict:
    """Update a catalog entry's value, descripcion, and/or dominio.

    The key is immutable — any 'key' in data is ignored.
    Value must be a JSON array if provided.

    Args:
        db: SQLAlchemy Session
        key: Catalog key to update
        data: dict with optional 'value', 'descripcion', 'dominio'

    Returns:
        dict: Updated catalog row

    Raises:
        ValueError: If key not found, or value is not a list
    """
    # Validate non-array value
    if "value" in data and data["value"] is not None:
        if not isinstance(data["value"], list):
            raise ValueError("El campo 'value' debe ser un array JSON")

    # Build SET clause dynamically
    set_parts = []
    params: dict[str, Any] = {"key": key}

    if "value" in data and data["value"] is not None:
        set_parts.append("value = CAST(:value AS jsonb)")
        params["value"] = json_lib.dumps(data["value"])
    if "descripcion" in data:
        set_parts.append("descripcion = :descripcion")
        params["descripcion"] = data.get("descripcion")
    if "dominio" in data:
        set_parts.append("dominio = :dominio")
        params["dominio"] = data.get("dominio")

    if not set_parts:
        # No fields to update — just fetch
        return get_catalogo(db, key)

    set_parts.append("updated_at = now()")

    row = db.execute(
        text(f"""
            UPDATE catalogos
            SET {', '.join(set_parts)}
            WHERE key = :key
            RETURNING key, value, descripcion, dominio, updated_at
        """),
        params,
    ).fetchone()

    if row is None:
        raise ValueError(f"Catálogo '{key}' no encontrado")

    db.commit()
    mapping = row._mapping
    val = mapping["value"]
    if not isinstance(val, list):
        val = []
    return {
        "key": mapping["key"],
        "values": val,
        "value_count": len(val),
        "descripcion": mapping["descripcion"],
        "dominio": mapping["dominio"],
        "updated_at": mapping["updated_at"],
    }


def delete_catalogo(db, key: str) -> dict:
    """Delete a catalog entry, checking for active rule references first.

    If active rules reference this key via cat_in, raises ValueError with
    the list of blocking rules. If only non-active rules (draft/retired),
    deletion proceeds with a warning.

    Args:
        db: SQLAlchemy Session
        key: Catalog key to delete

    Returns:
        dict: {'deleted': True} with optional 'warnings' key

    Raises:
        ValueError: If key not found, or active rules reference it
    """
    # Check existence
    existing = db.execute(
        text("SELECT key FROM catalogos WHERE key = :key"),
        {"key": key},
    ).fetchone()

    if existing is None:
        raise ValueError(f"Catálogo '{key}' no encontrado")

    # Check referencing condiciones with rule info
    refs = db.execute(
        text("""
            SELECT DISTINCT r.id AS regla_id, r.nombre, r.estado, r.version
            FROM condiciones cd
            JOIN reglas r ON r.id = cd.regla_id
            WHERE cd.operador = 'cat_in'
              AND cd.valor_esperado #>> '{}' = :key
        """),
        {"key": key},
    ).fetchall()

    if refs:
        active_rules = [
            {
                "regla_id": row._mapping["regla_id"],
                "nombre": row._mapping["nombre"],
                "estado": row._mapping["estado"],
            }
            for row in refs
            if row._mapping["estado"] == "active"
        ]
        non_active_rules = [
            {
                "regla_id": row._mapping["regla_id"],
                "nombre": row._mapping["nombre"],
                "estado": row._mapping["estado"],
            }
            for row in refs
            if row._mapping["estado"] != "active"
        ]

        if active_rules:
            raise ValueError(
                f"No se puede eliminar: {len(active_rules)} regla(s) activa(s) "
                f"referencian este catálogo"
            )

        # Only non-active rules — allow with warning
        db.execute(
            text("DELETE FROM catalogos WHERE key = :key"),
            {"key": key},
        )
        db.commit()
        return {
            "deleted": True,
            "warnings": {
                "message": "El catálogo tenía reglas que lo referenciaban (solo draft/retiradas)",
                "reglas": non_active_rules,
            },
        }

    # No references — safe to delete
    db.execute(
        text("DELETE FROM catalogos WHERE key = :key"),
        {"key": key},
    )
    db.commit()
    return {"deleted": True}


def get_catalogo_reglas(db, key: str) -> list[dict]:
    """Get all rules that reference a catalog key via cat_in conditions.

    Returns a list of rule dicts with id, nombre, dominio, estado, version, activo.
    Returns empty list if no rules reference the key.
    """
    rows = db.execute(
        text("""
            SELECT DISTINCT r.id, r.nombre, r.dominio, r.estado, r.version, r.activo
            FROM condiciones cd
            JOIN reglas r ON r.id = cd.regla_id
            WHERE cd.operador = 'cat_in'
              AND cd.valor_esperado #>> '{}' = :key
            ORDER BY r.nombre
        """),
        {"key": key},
    ).fetchall()

    return [
        {
            "id": row._mapping["id"],
            "nombre": row._mapping["nombre"],
            "dominio": row._mapping["dominio"],
            "estado": row._mapping["estado"],
            "version": row._mapping["version"],
            "activo": row._mapping["activo"],
        }
        for row in rows
    ]
