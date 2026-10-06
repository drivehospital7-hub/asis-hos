"""Gestión del catálogo grupos_error (CRUD total).

Los grupos son etiquetas en `reglas.grupo_error`; esta tabla es el
catálogo gestionable (crear/renombrar/desasignar) y la fuente de las
sugerencias del editor. Guardarrailes:

- Filas 'sistema' (formato propio) bloqueadas: renombrar/desasignar/
  eliminar requieren cambio de código (GRUPO_FORMATTERS).
- Renombrar hacia un nombre sistema también se bloquea (secuestro
  de formatter).
- Sin reglas afectadas no hay rename/unassign (nada que hacer).
"""

from __future__ import annotations

import logging

from sqlalchemy import func

from app.constants.grupo_error import NAMED_FORMATTER_GROUPS
from app.models import GrupoError, Regla

logger = logging.getLogger(__name__)


def list_grupos(db_session) -> list[dict]:
    """Catálogo + etiquetas en uso con conteo de reglas.

    Returns:
        Lista de {nombre, tipo, total_reglas, reglas_activas} ordenada
        por nombre. Incluye filas sin uso y etiquetas en uso sin fila
        (legado, tipo simple) para poder gestionarlas.
    """
    rows = db_session.query(GrupoError).all()
    catalogo = {r.nombre: r.tipo for r in rows}
    # Solo linaje vigente: retiradas y deprecated no cuentan (ensucian
    # la gestión: un grupo con 3 retiradas parecía "en uso").
    vigentes = Regla.estado.notin_(["retired", "deprecated"])
    counts = (
        db_session.query(Regla.grupo_error, func.count(Regla.id))
        .filter(Regla.grupo_error.isnot(None))
        .filter(Regla.grupo_error != "")
        .filter(vigentes)
        .group_by(Regla.grupo_error)
        .all()
    )
    in_use: dict[str, dict[str, int]] = {}
    for nombre, total in counts:
        in_use[nombre] = {"total": int(total), "activas": 0}
    if in_use:
        activas = (
            db_session.query(Regla.grupo_error, func.count(Regla.id))
            .filter(Regla.grupo_error.in_(list(in_use)))
            .filter(Regla.activo == True)  # noqa: E712
            .filter(vigentes)
            .group_by(Regla.grupo_error)
            .all()
        )
        for nombre, total in activas:
            in_use[nombre]["activas"] = int(total)

    nombres = sorted(set(catalogo) | set(in_use))
    return [
        {
            "nombre": nombre,
            "tipo": catalogo.get(nombre, "simple"),
            "total_reglas": in_use.get(nombre, {}).get("total", 0),
            "reglas_activas": in_use.get(nombre, {}).get("activas", 0),
        }
        for nombre in nombres
    ]


def _norm(nombre: str | None) -> str:
    return (nombre or "").strip()


def validate_rename(anterior: str, nuevo: str) -> tuple[str, str]:
    """Valida y normaliza un renombre. Raise ValueError si no procede."""
    anterior, nuevo = _norm(anterior), _norm(nuevo)
    if not anterior:
        raise ValueError("Grupo origen requerido")
    if not nuevo:
        raise ValueError("Grupo destino requerido")
    if anterior == nuevo:
        raise ValueError("El nombre nuevo es igual al actual")
    if anterior in NAMED_FORMATTER_GROUPS:
        raise ValueError(
            f"'{anterior}' es grupo de sistema (formato propio): "
            "renombrarlo rompería su render. Requiere cambio de código."
        )
    if nuevo in NAMED_FORMATTER_GROUPS:
        raise ValueError(
            f"'{nuevo}' es grupo de sistema: fusionar reglas ahí cambiaría "
            "su formato. Elegí otro nombre."
        )
    return anterior, nuevo


def create_grupo(db_session, nombre: str) -> dict:
    """Crea una etiqueta simple en el catálogo (nace para usarse)."""
    nombre = _norm(nombre)
    if not nombre:
        raise ValueError("Nombre requerido")
    if nombre in NAMED_FORMATTER_GROUPS:
        raise ValueError(f"'{nombre}' es grupo de sistema: ya existe.")
    existente = db_session.query(GrupoError).filter_by(nombre=nombre).first()
    if existente:
        raise ValueError(f"'{nombre}' ya existe en el catálogo.")
    db_session.add(GrupoError(nombre=nombre, tipo="simple"))
    db_session.commit()
    logger.info("Grupo creado '%s'", nombre)
    return {"nombre": nombre, "tipo": "simple"}


def rename_grupo(db_session, anterior: str, nuevo: str, responsible: str | None = None) -> dict:
    """Renombra una etiqueta en reglas + fila del catálogo."""
    anterior, nuevo = validate_rename(anterior, nuevo)
    afectadas = (
        db_session.query(Regla)
        .filter(Regla.grupo_error == anterior)
        .all()
    )
    fila = db_session.query(GrupoError).filter_by(nombre=anterior).first()
    if not afectadas:
        if fila is None or fila.tipo == "sistema":
            raise ValueError(f"'{anterior}' no está en uso: nada que renombrar.")
        fila.nombre = nuevo  # renombre de sugerencia sin uso
        db_session.commit()
        logger.info("Sugerencia renombrada '%s' → '%s' (sin reglas)", anterior, nuevo)
        return {"anterior": anterior, "nuevo": nuevo, "actualizadas": 0}
    for rule in afectadas:
        rule.grupo_error = nuevo
        rule.cambio_que = f"Grupo '{anterior}' → '{nuevo}'"
        if responsible:
            rule.cambio_responsable = responsible
    destino = db_session.query(GrupoError).filter_by(nombre=nuevo).first()
    if fila is not None and fila.tipo != "sistema":
        if destino is not None:
            db_session.delete(fila)  # merge: reglas ya movidas
        else:
            fila.nombre = nuevo
    if destino is None:
        db_session.add(GrupoError(nombre=nuevo, tipo="simple"))
    db_session.commit()
    logger.info("Grupo renombrado '%s' → '%s' (%d reglas)", anterior, nuevo, len(afectadas))
    return {"anterior": anterior, "nuevo": nuevo, "actualizadas": len(afectadas)}


def delete_grupo(db_session, grupo: str) -> dict:
    """Borra una fila del catálogo. Solo sin reglas y no sistema."""
    grupo = _norm(grupo)
    if not grupo:
        raise ValueError("Grupo requerido")
    if grupo in NAMED_FORMATTER_GROUPS:
        raise ValueError(f"'{grupo}' es grupo de sistema: no se elimina.")
    fila = db_session.query(GrupoError).filter_by(nombre=grupo).first()
    if fila is None:
        raise ValueError(f"'{grupo}' no está en el catálogo.")
    if fila.tipo == "sistema":
        raise ValueError(f"'{grupo}' es grupo de sistema: no se elimina.")
    en_uso = (
        db_session.query(func.count(Regla.id))
        .filter(Regla.grupo_error == grupo)
        .filter(Regla.estado.notin_(["retired", "deprecated"]))
        .scalar()
    )
    if en_uso:
        raise ValueError(
            f"'{grupo}' tiene {en_uso} regla(s): desasigná primero."
        )
    db_session.delete(fila)
    db_session.commit()
    logger.info("Grupo eliminado del catálogo '%s'", grupo)
    return {"grupo": grupo, "eliminado": True}


def unassign_grupo(db_session, grupo: str, responsible: str | None = None) -> dict:
    """Desasigna una etiqueta (reglas a auto) y borra su fila si es simple."""
    grupo = _norm(grupo)
    if not grupo:
        raise ValueError("Grupo requerido")
    if grupo in NAMED_FORMATTER_GROUPS:
        raise ValueError(
            f"'{grupo}' es grupo de sistema (formato propio): "
            "desasignarlo rompería su render. Requiere cambio de código."
        )
    afectadas = (
        db_session.query(Regla)
        .filter(Regla.grupo_error == grupo)
        .all()
    )
    if not afectadas:
        raise ValueError(f"'{grupo}' no está en uso: nada que desasignar.")
    for rule in afectadas:
        rule.grupo_error = None
        rule.cambio_que = f"Grupo '{grupo}' desasignado (auto)"
        if responsible:
            rule.cambio_responsable = responsible
    fila = db_session.query(GrupoError).filter_by(nombre=grupo).first()
    if fila is not None and fila.tipo != "sistema":
        db_session.delete(fila)
    db_session.commit()
    logger.info("Grupo desasignado '%s' (%d reglas)", grupo, len(afectadas))
    return {"grupo": grupo, "actualizadas": len(afectadas)}
