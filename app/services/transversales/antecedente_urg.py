"""Antecedente de urgencias/hospitalizacion dentro de 24h (precomputo).

Para cada fila, determina si el mismo paciente (Nº Identificacion) tuvo
una factura de tipo Urgencias u Hospitalizacion con Fec. Factura entre
0 y 24 horas ANTES que la fila actual. Se usa como excepcion de reglas
de contratado (ej. intramural por evento tras ingreso CAP por urgencias).

Se computa en el exporter sobre el RowStore, ANTES de evaluar: las filas
llevan la clave ``tuvo_urg_hosp_24h`` (bool) y el motor la lee como un
``invoice.*`` mas (sin provider nuevo).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

TIPOS_URGENCIA = frozenset({"urgencias", "hospitalización"})
VENTANA_HORAS = 24


def _parse_fecha(value: Any):
    """Parse tolerante (mismos formatos que DateProvider)."""
    from app.services.engine.providers import DateProvider

    return DateProvider._parse_date(value)


def compute_urg_hosp_24h_flags(rows: list[dict[str, Any]]) -> int:
    """Marca in-place ``tuvo_urg_hosp_24h`` en cada fila. Retorna cuantas quedaron en True.

    Agrupa por identificacion para no hacer O(n^2): cada fila solo se
    compara con las de su mismo paciente.
    """
    por_paciente: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        doc = row.get("identificacion")
        doc_key = str(doc).strip() if doc is not None else ""
        if doc_key:
            por_paciente.setdefault(doc_key, []).append(i)

    def _es_urgencia(r: dict[str, Any]) -> bool:
        tipo = r.get("tipo_factura_descripcion")
        return isinstance(tipo, str) and tipo.strip().lower() in TIPOS_URGENCIA

    marcados = 0
    for doc_key, idxs in por_paciente.items():
        # (indice fila, fecha) de urgencias/hospitalizacion de este paciente.
        urg_fechas: list[tuple[int, Any]] = []
        for j in idxs:
            rj = rows[j]
            if not isinstance(rj, dict) or not _es_urgencia(rj):
                continue
            fj = _parse_fecha(rj.get("fec_factura"))
            if fj is not None:
                urg_fechas.append((j, fj))
        if not urg_fechas:
            for j in idxs:
                if isinstance(rows[j], dict):
                    rows[j]["tuvo_urg_hosp_24h"] = False
            continue
        for j in idxs:
            rj = rows[j]
            if not isinstance(rj, dict):
                continue
            fi = _parse_fecha(rj.get("fec_factura"))
            hit = False
            if fi is not None:
                for k, fj in urg_fechas:
                    if k == j:
                        continue  # la fila no es antecedente de si misma
                    delta_horas = (fi - fj).total_seconds() / 3600.0
                    if 0 <= delta_horas <= VENTANA_HORAS:
                        hit = True
                        break
            rj["tuvo_urg_hosp_24h"] = hit
            if hit:
                marcados += 1
    # Filas sin identificacion: flag explicito False.
    for row in rows:
        if isinstance(row, dict) and "tuvo_urg_hosp_24h" not in row:
            row["tuvo_urg_hosp_24h"] = False
    logger.info(
        "Antecedente urg/hosp 24h: %d filas marcadas sobre %d",
        marcados, len(rows),
    )
    return marcados
