"""Búsqueda de facturas por cadena de códigos (Traslado de Facturas).

Parsea la cadena pegada por el usuario a núcleos FEV/CAP (reusa
``extract_code`` de cruce_produccion.matcher, NO duplicar regex) y los
cruza contra el índice del cache del watcher de monitoreo.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.services.cruce_produccion.matcher import extract_code

logger = logging.getLogger(__name__)

_SPLIT_RE = re.compile(r"[,;\s]+")


def parse_codigos(cadena: str | None) -> list[str]:
    """Parsea una cadena suelta a núcleos de código únicos en orden.

    Separa por coma, punto-coma, espacios y saltos de línea; extrae el
    núcleo FEV/CAP de cada fragmento (``extract_code``); ignora los
    fragmentos sin código y deduplica preservando el primer orden.

    Args:
        cadena: Texto pegado por el usuario (puede ser None/vacío).

    Returns:
        Lista de núcleos upper (``FEV123``, ``CAP001``), sin duplicados.
    """
    if not cadena:
        return []
    codigos: list[str] = []
    seen: set[str] = set()
    for fragment in _SPLIT_RE.split(cadena):
        code = extract_code(fragment)
        if code is not None and code not in seen:
            seen.add(code)
            codigos.append(code)
    logger.info("parse_codigos: %d códigos únicos", len(codigos))
    return codigos


def _under_roots(full_path: str, roots: list[str]) -> bool:
    """Prefijo normalizado: el path vive bajo una de las raíces."""
    norm_path = full_path.replace("\\", "/")
    return any(
        norm_path.startswith(root.replace("\\", "/")) for root in roots
    )


def split_roots(
    raices: list[str], watcher_roots: list[str] | None
) -> tuple[list[str], list[str]]:
    """Particiona raíces pedidas en (cubiertas, no_cubiertas).

    Cubierta = prefijo normalizado bajo alguna watcher-root (su cache
    ya la contiene); no cubierta = requiere `detect_all` fresco.
    Sin watcher-roots, todo es no cubierto.

    Args:
        raices: Raíces pedidas (texto libre del usuario o config).
        watcher_roots: Raíces escaneadas por el watcher (puede ser None).

    Returns:
        Tupla (cubiertas, no_cubiertas) preservando el orden pedido.
    """
    cubiertas: list[str] = []
    no_cubiertas: list[str] = []
    for raiz in raices:
        if _under_roots(raiz, watcher_roots or []):
            cubiertas.append(raiz)
        else:
            no_cubiertas.append(raiz)
    logger.info(
        "split_roots: %d cubiertas, %d no cubiertas",
        len(cubiertas), len(no_cubiertas),
    )
    return cubiertas, no_cubiertas


def buscar(
    codigos: list[str],
    facturas: list[Any],
    roots: list[str] | None = None,
) -> dict[str, list[Any]]:
    """Cruza códigos contra facturas del watcher cache.

    Indexa por núcleo (``extract_code`` de ``invoice_code``); la primera
    factura decide ante duplicados de código.

    Args:
        codigos: Núcleos upper (salida de :func:`parse_codigos`).
        facturas: ``InvoiceRecord`` del watcher (``invoice_code``,
            ``full_path``, ``facturador``).
        roots: Si se provee (no vacío), solo se indexan facturas bajo
            esas raíces (prefijo normalizado).

    Returns:
        ``{"encontradas": [{"codigo", "full_path", "facturador"}],
        "no_encontradas": [codigo]}``.
    """
    pool = facturas
    if roots:
        pool = [inv for inv in facturas if _under_roots(inv.full_path, roots)]
    index: dict[str, Any] = {}
    for inv in pool:
        code = extract_code(getattr(inv, "invoice_code", None))
        if code and code not in index:
            index[code] = inv
    encontradas: list[dict[str, str]] = []
    no_encontradas: list[str] = []
    for code in codigos:
        inv = index.get(code)
        if inv is None:
            no_encontradas.append(code)
        else:
            encontradas.append({
                "codigo": code,
                "full_path": inv.full_path,
                "facturador": inv.facturador,
            })
    logger.info(
        "buscar: %d encontradas, %d no encontradas",
        len(encontradas),
        len(no_encontradas),
    )
    return {"encontradas": encontradas, "no_encontradas": no_encontradas}
