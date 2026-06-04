"""Tests para la migración de constants.py a package app/constants/.

Verifica que:
1. `from app.constants import X` sigue funcionando (vía constants.py existente O re-export del package)
2. Los nuevos módulos domain existen como archivos y contienen las constantes correctas
3. No hay regresión en las constantes que usan los servicios
"""

from __future__ import annotations

from pathlib import Path

# =============================================================================
# Approval test: from app.constants import X (current API — siempre funciona)
# =============================================================================
# NOTA: Ahora app/constants.py fue eliminado (Fase 7 cleanup).
# Python resuelve app.constants al package app/constants/.

from app.constants import (  # noqa: E402
    ALLOWED_EXCEL_SUFFIXES,
    AREA_EQUIPOS_BASICOS,
    AREA_ODONTOLOGIA,
    AREA_URGENCIAS,
    CANTIDAD_CONSULTAS_MIN,
    CANTIDAD_MAX,
    CANTIDAD_PYP_MIN,
    CENTRO_COSTO_EQUIPOS_BASICOS,
    CENTRO_COSTO_EXTRAMURAL,
    CENTRO_COSTO_ODONTOLOGIA,
    CODIGOS_MAL_CAPITADO,
    COLOR_GREEN,
    COLOR_GREEN_DARK,
    COLOR_GREEN_LIGHT,
    COLOR_RED,
    COLOR_RED_DARK,
    COLOR_RED_LIGHT,
    COLOR_YELLOW,
    COLOR_YELLOW_DARK,
    COLOR_YELLOW_LIGHT,
    COLUMNS_TO_KEEP,
    CONVENIO_ASISTENCIAL,
    CONVENIO_PYP,
    DATA_ROW_BACKGROUND_COLOR,
    ENTIDAD_REQUERIDA_CAP,
    EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN,
    EQUIPOS_BASICOS_CANTIDAD_MAX,
    EQUIPOS_BASICOS_CANTIDAD_PYP_MIN,
    EQUIPOS_BASICOS_COLUMNS_TO_KEEP,
    EQUIPOS_BASICOS_REVISION_HEADERS,
    EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD,
    EQUIPOS_BASICOS_TARGET_PROCEDURES,
    HEADER_BACKGROUND_COLOR,
    HEADER_BORDER_COLOR,
    HORAS_POR_DIA,
    IMAGENES_ALLOWED_TYPES,
    IMAGENES_DIR,
    IMAGENES_MAX_PER_OBSERVACION,
    IMAGENES_MAX_SIZE_MB,
    PREFIJO_FACTURA_CAP,
    PREFIJO_FACTURA_MAL_CAPITADO,
    PROFESIONALES_EQUIPOS_BASICOS,
    PROFESIONALES_ODONTOLOGIA,
    PROFESIONALES_ODONTOLOGIA_VALIDACION,
    PROFESIONALES_URGENCIAS,
    PYP_CODES_HIGIENISTA,
    PYP_CUPS_CODES,
    REVISION_HEADERS,
    REVISION_SHEET,
    RUTA_DUPLICADA_THRESHOLD,
    TARGET_PROCEDURES,
    TIPO_USUARIO_VALORES,
    URGENCIA_COLUMNS_TO_KEEP,
    URGENCIA_DATA_ROW_BACKGROUND_COLOR,
    URGENCIA_ENTIDAD_CONTRATO,
    URGENCIA_ENTIDAD_MULTIPLE_CONTRATO,
    URGENCIA_HEADER_BACKGROUND_COLOR,
    URGENCIA_HEADER_BORDER_COLOR,
    URGENCIA_REVISION_HEADERS,
)

_CONSTANTS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "constants"


# =============================================================================
# Test: Los nuevos archivos del package existen
# =============================================================================


class TestConstantsPackageStructure:
    """Verifica que todos los archivos del package existen."""

    def test_package_init_exists(self):
        assert _CONSTANTS_DIR.exists()
        assert (_CONSTANTS_DIR / "__init__.py").exists()

    def test_base_module_exists(self):
        assert (_CONSTANTS_DIR / "base.py").exists()

    def test_columnas_module_exists(self):
        assert (_CONSTANTS_DIR / "columnas.py").exists()

    def test_colores_module_exists(self):
        assert (_CONSTANTS_DIR / "colores.py").exists()

    def test_odontologia_module_exists(self):
        assert (_CONSTANTS_DIR / "odontologia.py").exists()

    def test_urgencias_module_exists(self):
        assert (_CONSTANTS_DIR / "urgencias.py").exists()


# =============================================================================
# Test: from app.constants import X funciona (API pública)
# =============================================================================


class TestConstantsAPI:
    """Verifica que la API pública desde app.constants funciona."""

    def test_allowed_excel_suffixes(self):
        assert ALLOWED_EXCEL_SUFFIXES == frozenset({".xlsx", ".xls", ".xlsm", ".xlsb"})

    def test_sheets(self):
        assert REVISION_SHEET == "Revision"

    def test_convenios(self):
        assert CONVENIO_ASISTENCIAL == "Asistencial"
        assert CONVENIO_PYP == "Promoción y Prevención"

    def test_areas(self):
        assert AREA_ODONTOLOGIA == "odontologia"
        assert AREA_URGENCIAS == "urgencias"
        assert AREA_EQUIPOS_BASICOS == "equipos_basicos"

    def test_tipo_usuario_valores(self):
        assert "SUBSIDIADO" in TIPO_USUARIO_VALORES

    def test_umbrales(self):
        assert RUTA_DUPLICADA_THRESHOLD == 3
        assert CANTIDAD_CONSULTAS_MIN == 2
        assert CANTIDAD_MAX == 10
        assert CANTIDAD_PYP_MIN == 3

    def test_imagenes(self):
        assert IMAGENES_DIR == "data/imagenes"
        assert IMAGENES_MAX_PER_OBSERVACION == 3
        assert ".pdf" in IMAGENES_ALLOWED_TYPES
        assert IMAGENES_MAX_SIZE_MB == 20

    def test_horas_por_dia(self):
        assert HORAS_POR_DIA == 24

    def test_columns_to_keep(self):
        assert "Número Factura" in COLUMNS_TO_KEEP
        assert "Vlr. Procedimiento" in COLUMNS_TO_KEEP
        assert "Centro Costo" in COLUMNS_TO_KEEP

    def test_urgencia_columns_to_keep(self):
        assert "Código Tipo Procedimiento" in URGENCIA_COLUMNS_TO_KEEP
        assert "Laboratorio" in URGENCIA_COLUMNS_TO_KEEP
        assert "Número Factura" in URGENCIA_COLUMNS_TO_KEEP

    def test_centro_costos(self):
        assert CENTRO_COSTO_ODONTOLOGIA == "ODONTOLOGIA"
        assert CENTRO_COSTO_EXTRAMURAL == "SERVICIOS ODONTOLOGIA -EXTRAMURALES"
        assert CENTRO_COSTO_EQUIPOS_BASICOS == "EQUIPOS BASICOS ODONTOLOGIA"

    def test_revision_headers(self):
        assert REVISION_HEADERS[1] == "Tipo de error"
        assert len(REVISION_HEADERS) == 6

    def test_urgencia_revision_headers(self):
        assert URGENCIA_REVISION_HEADERS[1] == "Tipo de error"
        assert len(URGENCIA_REVISION_HEADERS) == 6

    def test_colores_verdes(self):
        assert COLOR_GREEN_LIGHT == "C6EFCE"
        assert COLOR_GREEN_DARK == "63BE7B"
        assert COLOR_GREEN == "C6EFCE"

    def test_colores_amarillos(self):
        assert COLOR_YELLOW_LIGHT == "FFEB9C"
        assert COLOR_YELLOW_DARK == "FFC000"
        assert COLOR_YELLOW == "FFEB9C"

    def test_colores_rojos(self):
        assert COLOR_RED_LIGHT == "FFC7CE"
        assert COLOR_RED_DARK == "FF6B6B"
        assert COLOR_RED == "FFC7CE"

    def test_header_colors(self):
        assert HEADER_BACKGROUND_COLOR == "DCE6F1"
        assert HEADER_BORDER_COLOR == "4472C4"

    def test_data_row_colors(self):
        assert DATA_ROW_BACKGROUND_COLOR == "F2F6FA"

    def test_urgencia_colors(self):
        assert URGENCIA_HEADER_BACKGROUND_COLOR == "FFCCCC"
        assert URGENCIA_HEADER_BORDER_COLOR == "FF6B6B"
        assert URGENCIA_DATA_ROW_BACKGROUND_COLOR == "FFF0F0"

    def test_pyp_cups_codes(self):
        assert "890203" in PYP_CUPS_CODES
        assert "997002" in PYP_CUPS_CODES

    def test_pyp_higienista(self):
        assert "997002" in PYP_CODES_HIGIENISTA

    def test_target_procedures(self):
        assert "Control de Placa Bacteriana" in TARGET_PROCEDURES

    def test_profesionales_odontologia(self):
        assert "001" in PROFESIONALES_ODONTOLOGIA
        assert PROFESIONALES_ODONTOLOGIA["001"]["nombre"] == "ARIAS MOREANO LAURA MELISSA"

    def test_profesionales_odontologia_validacion(self):
        assert "03424" in PROFESIONALES_ODONTOLOGIA_VALIDACION
        assert PROFESIONALES_ODONTOLOGIA_VALIDACION["03424"]["tipo"] == "ODONTOLOGO"

    def test_mal_capitado(self):
        assert "G03XB01" in CODIGOS_MAL_CAPITADO
        assert PREFIJO_FACTURA_MAL_CAPITADO == "FEV"
        assert PREFIJO_FACTURA_CAP == "CAP"
        assert ENTIDAD_REQUERIDA_CAP == "ESS118"

    def test_profesionales_urgencias(self):
        assert "03568" in PROFESIONALES_URGENCIAS
        assert PROFESIONALES_URGENCIAS["03568"]["tipo"] == "TRABAJADORA SOCIAL"

    def test_urgencia_entidad_contrato(self):
        assert URGENCIA_ENTIDAD_CONTRATO["86000"] == "919"
        assert URGENCIA_ENTIDAD_CONTRATO["5177"] == "917"

    def test_urgencia_entidad_multiple_contrato(self):
        assert "910" in URGENCIA_ENTIDAD_MULTIPLE_CONTRATO["MIN001"]
        assert "918" in URGENCIA_ENTIDAD_MULTIPLE_CONTRATO["MIN001"]

    def test_equipos_basicos_constants(self):
        assert EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN == 2
        assert EQUIPOS_BASICOS_CANTIDAD_PYP_MIN == 3
        assert EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD == 3
        assert "Control de Placa Bacteriana" in EQUIPOS_BASICOS_TARGET_PROCEDURES

    def test_equipos_basicos_columns_reference(self):
        assert EQUIPOS_BASICOS_COLUMNS_TO_KEEP == COLUMNS_TO_KEEP

    def test_equipos_basicos_revision_headers(self):
        assert EQUIPOS_BASICOS_REVISION_HEADERS[1] == "Tipo de error"
        assert len(EQUIPOS_BASICOS_REVISION_HEADERS) == 6

    def test_profesionales_equipos_basicos(self):
        assert "03764" in PROFESIONALES_EQUIPOS_BASICOS
        assert PROFESIONALES_EQUIPOS_BASICOS["03764"]["tipo"] == "ODONTOLOGO"

    def test_default_templates(self):
        """DEFAULT_TEMPLATES is a list of 3 dicts with lowercase nombres and valid permisos."""
        from app.constants.base import DEFAULT_TEMPLATES, ALLOWED_PERMISOS
        assert isinstance(DEFAULT_TEMPLATES, list)
        assert len(DEFAULT_TEMPLATES) == 3
        nombres = {t["nombre"] for t in DEFAULT_TEMPLATES}
        assert nombres == {"odontologia", "urgencias", "auditor"}
        for t in DEFAULT_TEMPLATES:
            assert "nombre" in t
            assert "descripcion" in t
            assert "permisos" in t
            assert len(t["permisos"]) >= 1
            for p in t["permisos"]:
                assert p in ALLOWED_PERMISOS


