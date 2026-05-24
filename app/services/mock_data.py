"""Mock data for development environment.

Provides realistic sample data for every view when running in development mode.
This allows visual testing without a real database or Excel files.

Usage:
    from app.services.mock_data import get_mock_data

    # In a route:
    if current_app.config.get("ENV") == "development":
        context.update(get_mock_data(request.endpoint))
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _kpis_sample() -> dict:
    return {
        "total": 156,
        "pendientes": 23,
        "resueltas": 133,
    }


def _errores_sample() -> list[dict]:
    """Sample errors for control_errores view."""
    return [
        {
            "id": 1,
            "factura": "CAP447148",
            "creado_en": (datetime.now() - timedelta(hours=3)).isoformat(),
            "tipo_error": "Clínico",
            "observacion": "Historia clínica incompleta — falta firma del médico tratante",
            "responsable": "ALEJANDRA ESPAÑA",
            "estado": "S",
            "imagenes_count": 0,
            "observacion_facturador": "",
        },
        {
            "id": 2,
            "factura": "CAP447149",
            "creado_en": (datetime.now() - timedelta(days=1)).isoformat(),
            "tipo_error": "Administrativo",
            "observacion": "Código CUPS no corresponde al procedimiento realizado",
            "responsable": "CARLOS OMAR",
            "estado": "S",
            "imagenes_count": 2,
            "observacion_facturador": "Verificar con el área de facturación",
        },
        {
            "id": 3,
            "factura": "FEV89231",
            "creado_en": (datetime.now() - timedelta(days=5)).isoformat(),
            "tipo_error": "Farmacológico",
            "observacion": "Medicamento no incluido en el POS — requiere autorización",
            "responsable": "DANIELA PAEZ",
            "estado": "N",
            "imagenes_count": 0,
            "observacion_facturador": "",
        },
        {
            "id": 4,
            "factura": "FEV89232",
            "creado_en": (datetime.now() - timedelta(weeks=2)).isoformat(),
            "tipo_error": "Equipamiento",
            "observacion": "Insumo no registrado en el inventario del servicio",
            "responsable": "ANGIE ARIAS",
            "estado": "N",
            "imagenes_count": 0,
            "observacion_facturador": "Ya se realizó el ajuste en inventario",
        },
        {
            "id": 5,
            "factura": "CAP448001",
            "creado_en": (datetime.now() - timedelta(hours=8)).isoformat(),
            "tipo_error": "Comunicación",
            "observacion": "Orden médica ilegible — solicitar transcripción",
            "responsable": "ALEJANDRA ESPAÑA",
            "estado": "S",
            "imagenes_count": 1,
            "observacion_facturador": "",
        },
        {
            "id": 6,
            "factura": "CAP448002",
            "creado_en": (datetime.now() - timedelta(days=3)).isoformat(),
            "tipo_error": "Clínico",
            "observacion": "Paciente sin carné de afiliación al momento de la atención",
            "responsable": "CARLOS OMAR",
            "estado": "N",
            "imagenes_count": 0,
            "observacion_facturador": "Carné entregado el día siguiente",
        },
    ]


def _schedule_sample() -> list[dict]:
    """Sample schedule for abiertas_urgencias view."""
    today = datetime.now()
    return [
        {
            "dia": (today + timedelta(days=i)).strftime("%A"),
            "fecha": (today + timedelta(days=i)).strftime("%Y-%m-%d"),
            "turno": "Mañana" if i % 3 != 0 else "Tarde",
            "medico": f"Médico {chr(65 + i)}",
            "enfermera": f"Enfermera {chr(75 + i)}",
        }
        for i in range(7)
    ]


def get_mock_data(view_name: str) -> dict:
    """Dev-only: retorna datos mock para desarrollo.

    Args:
        view_name: The Flask endpoint name (e.g., 'home.home_page',
                   'control_errores.control_errores_page') or short name
                   like 'home', 'control_errores'.

    Returns:
        A dict with mock data appropriate for the given view.
        Returns empty dict for unknown views.
    """
    # Support both short names and full endpoint names
    _short = view_name.split(".")[0] if "." in view_name else view_name

    if _short in ("home",):
        return {
            "kpis": _kpis_sample(),
            "mock_data": True,
        }

    if _short in ("control_errores",):
        return {
            "errores": _errores_sample(),
            "kpis": _kpis_sample(),
            "mock_data": True,
        }

    if _short in ("abiertas_urgencias",):
        return {
            "schedule": _schedule_sample(),
            "mock_data": True,
        }

    if _short in ("excel_headers",):
        return {
            "profesionales": [
                "Dr. Juan Pérez",
                "Dra. María García",
                "Dr. Carlos López",
            ],
            "mock_data": True,
        }

    logger.debug("No mock data for view: %s", view_name)
    return {}
