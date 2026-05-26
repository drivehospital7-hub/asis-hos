"""Registro central de detectores por tipo de factura.

Mapea valores exactos de "Tipo Factura Descripción" a listas de detectores callables.
Cada entrada incluye automáticamente los detectores transversales.
"""

from __future__ import annotations

from typing import Callable


# Transversal detectors — imported eagerly (they exist and have no tipo_factura dependency)
def _get_transversal_detectors() -> list[Callable]:
    from app.services.transversales import (
        detect_decimales,
        detect_tipo_documento_edad,
        detect_codigo_entidad_vs_entidad_afiliacion,
        detect_tipo_usuario,
    )
    return [
        detect_decimales,
        detect_tipo_documento_edad,
        detect_codigo_entidad_vs_entidad_afiliacion,
        detect_tipo_usuario,
    ]


def get_detectors(tipo_factura: str) -> list[Callable]:
    """Returns detector callables for a tipo_factura. Empty list for unknown/falsy values.

    Args:
        tipo_factura: Valor de la columna "Tipo Factura Descripción" en el Excel.

    Returns:
        Lista de funciones detectoras (callables). Vacía si el tipo es desconocido.
    """
    if not tipo_factura:
        return []

    transversales = _get_transversal_detectors()

    if tipo_factura == "Urgencias":
        from app.services.urgencias.centro_costo_urgencias import (
            detect_centro_costo_urgencias,
        )
        from app.services.urgencias.ide_contrato_urgencias import (
            detect_ide_contrato_urgencias,
        )
        from app.services.urgencias.cups_equivalentes import detect_cups_equivalentes
        from app.services.urgencias.sala_observacion import detect_sala_observacion
        from app.services.urgencias.cantidades_urgencias import (
            detect_cantidades_urgencias,
        )
        from app.services.urgencias.cantidades_soat_urgencias import (
            detect_cantidades_soat_urgencias,
        )
        from app.services.hospitalizacion.cantidades_soat_hospitalizacion import (
            detect_cantidades_soat_hospitalizacion,
        )
        from app.services.hospitalizacion.cantidades_hospitalizacion import (
            detect_cantidades_hospitalizacion,
        )
        from app.services.hospitalizacion.hospitalizacion_codes import (
            detect_hospitalizacion_codes,
        )
        from app.services.urgencias.mal_capitado import detect_mal_capitado
        from app.services.urgencias.codigos_sin_db import get_codigos_no_en_db_ess118
        from app.services.urgencias.ide_contrato_reverse import detect_ide_contrato_reverse_urgencias
        from app.services.urgencias.profesionales_urgencias import detect_profesionales_urgencias
        from app.services.transversales.detect_copago_entidad import (
            detect_copago_entidad_urgencias,
        )
        from app.services.urgencias.revision_cantidad import detect_revision_cantidad_urgencias
        from app.services.urgencias.revision_entidad_86 import detect_revision_entidad_86_urgencias
        from app.services.urgencias.duplicados_farmacia import detect_duplicados_farmacia

        return transversales + [
            detect_centro_costo_urgencias,
            detect_ide_contrato_urgencias,
            detect_cups_equivalentes,
            detect_sala_observacion,
            detect_cantidades_urgencias,
            detect_cantidades_soat_urgencias,
            detect_cantidades_soat_hospitalizacion,
            detect_cantidades_hospitalizacion,
            detect_hospitalizacion_codes,
            detect_mal_capitado,
            get_codigos_no_en_db_ess118,
            detect_ide_contrato_reverse_urgencias,
            detect_profesionales_urgencias,
            detect_copago_entidad_urgencias,
            detect_revision_cantidad_urgencias,
            detect_revision_entidad_86_urgencias,
            detect_duplicados_farmacia,
        ]

    if tipo_factura == "Hospitalización":
        # Per-tipo package created in phase 5
        from app.services.hospitalizacion.detect_all import (
            _get_hospitalizacion_detectors,
        )
        return transversales + _get_hospitalizacion_detectors()

    if tipo_factura == "Intramural":
        # Per-tipo package created in phase 5
        from app.services.intramural.detect_all import (
            _get_intramural_detectors,
        )
        return transversales + _get_intramural_detectors()

    if tipo_factura == "Ambulatoria":
        # Per-tipo package created in phase 5
        from app.services.ambulatoria.detect_all import (
            _get_ambulatoria_detectors,
        )
        return transversales + _get_ambulatoria_detectors()

    return []
