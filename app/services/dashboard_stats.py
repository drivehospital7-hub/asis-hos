"""Estadisticas del panel principal (dashboard).

Agrega las novedades del control de novedades del mes actual:
total, pendientes (estado ``S``), resueltas (estado ``N``) y tasa de
resolucion. Lee con ``listar_errores`` sin filtros de propietario: el
panel muestra el estado global del cierre.
"""

import logging
from datetime import datetime

from app.utils.errores_storage import listar_errores

logger = logging.getLogger(__name__)

MESES_ES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


def month_label_es(now: datetime) -> str:
    """Etiqueta del mes en espanol, ej. ``Octubre 2026``."""
    return f"{MESES_ES[now.month - 1]} {now.year}"


def get_dashboard_stats(now: datetime | None = None) -> dict:
    """Calcular los KPIs del panel para el mes actual.

    Response Format: ``{"status", "data", "errors"}`` (nunca "warning").
    """
    try:
        today = now or datetime.now()
        month_key = today.strftime("%Y-%m")
        label = month_label_es(today)

        errores = listar_errores()
        del_mes = [e for e in errores if str(e.get("creado_en", ""))[:7] == month_key]

        total = len(del_mes)
        pendientes = sum(1 for e in del_mes if e.get("estado") == "S")
        resueltos = sum(1 for e in del_mes if e.get("estado") == "N")
        tasa = round(resueltos / total * 100) if total else 0

        kpis = [
            {
                "label": "Novedades del mes",
                "value": str(total),
                "trend": f"Creadas en {label}",
                "icon": "inbox",
                "tone": "info",
            },
            {
                "label": "Pendientes",
                "value": str(pendientes),
                "trend": f"{total - pendientes} al día · {label}" if total else "Sin novedades este mes",
                "icon": "clock",
                "tone": "warning",
            },
            {
                "label": "Resueltas este mes",
                "value": str(resueltos),
                "trend": f"{tasa}% de resolución · {label}",
                "icon": "check-circle",
                "tone": "success",
            },
            {
                "label": "Tasa de resolución",
                "value": f"{tasa}%",
                "trend": f"{resueltos} de {total} resueltas",
                "icon": "trending-up",
                "tone": "primary",
            },
        ]

        logger.info(
            "KPIs dashboard %s: total=%d pendientes=%d resueltos=%d",
            month_key,
            total,
            pendientes,
            resueltos,
        )
        return {
            "status": "success",
            "data": {
                "month_key": month_key,
                "month_label": label,
                "kpis": kpis,
            },
            "errors": [],
        }
    except Exception as e:
        logger.exception("Error calculando KPIs del dashboard")
        return {"status": "error", "data": {}, "errors": [str(e)]}
