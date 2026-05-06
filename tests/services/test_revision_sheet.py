"""Tests para app/services/revision_sheet.py."""

from __future__ import annotations

import pytest
from openpyxl import Workbook

from app.services.revision_sheet import (
    _normalize_header,
    _normalize_invoice,
    _get_column_indices,
    _detect_decimals,
    _detect_doble_tipo_procedimiento,
    _detect_ruta_duplicada,
    _detect_cantidades_anomalas,
    _write_column,
    _build_urgencias_normalized_rows,
    create_revision_sheet,
    REVISION_HEADERS,
    URGENCIA_REVISION_HEADERS,
)
from app.constants import (
    CONVENIO_ASISTENCIAL,
    CONVENIO_PYP,
    REVISION_SHEET,
    TARGET_PROCEDURES,
    PYP_CUPS_CODES,
)


@pytest.fixture
def workbook_with_invoice_data() -> Workbook:
    """Crea un workbook con datos de facturas para pruebas."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"

    # Headers (incluye Código para validar convenio)
    headers = [
        "Número Factura",
        "Vlr. Subsidiado",
        "Vlr. Procedimiento",
        "Tipo Procedimiento",
        "Código",
        "Procedimiento",
        "Nº Identificación",
        "Convenio Facturado",
        "Cantidad",
    ]
    for col, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=header)

    return wb


def add_invoice_row(
    ws,
    row: int,
    numero: str,
    vlr_sub: float = 1000,
    vlr_proc: float = 500,
    tipo_proc: str = "Consultas",
    codigo: str = "890101",
    procedimiento: str = "Consulta General",
    identificacion: str = "123456",
    convenio: str = CONVENIO_ASISTENCIAL,
    cantidad: int = 1,
) -> None:
    """Helper para agregar una fila de factura."""
    ws.cell(row=row, column=1, value=numero)
    ws.cell(row=row, column=2, value=vlr_sub)
    ws.cell(row=row, column=3, value=vlr_proc)
    ws.cell(row=row, column=4, value=tipo_proc)
    ws.cell(row=row, column=5, value=codigo)
    ws.cell(row=row, column=6, value=procedimiento)
    ws.cell(row=row, column=7, value=identificacion)
    ws.cell(row=row, column=8, value=convenio)
    ws.cell(row=row, column=9, value=cantidad)


class TestNormalizeHeader:
    """Tests para _normalize_header."""

    def test_normaliza_a_minusculas(self) -> None:
        """Debe convertir a minúsculas."""
        assert _normalize_header("NUMERO FACTURA") == "numero factura"

    def test_elimina_espacios_extra(self) -> None:
        """Debe eliminar espacios al inicio y final."""
        assert _normalize_header("  header  ") == "header"

    def test_none_retorna_string_vacio(self) -> None:
        """None debe retornar string vacío."""
        assert _normalize_header(None) == ""


class TestNormalizeInvoice:
    """Tests para _normalize_invoice."""

    def test_convierte_float_entero_a_string(self) -> None:
        """Float sin decimales debe convertirse a string entero."""
        assert _normalize_invoice(12345.0) == "12345"

    def test_mantiene_string(self) -> None:
        """String debe mantenerse (strippeado)."""
        assert _normalize_invoice("FAC-001") == "FAC-001"
        assert _normalize_invoice("  FAC-002  ") == "FAC-002"

    def test_none_retorna_none(self) -> None:
        """None debe retornar None."""
        assert _normalize_invoice(None) is None

    def test_string_vacio_retorna_none(self) -> None:
        """String vacío debe retornar None."""
        assert _normalize_invoice("") is None


class TestGetColumnIndices:
    """Tests para _get_column_indices."""

    def test_mapea_headers_conocidos(self) -> None:
        """Debe mapear headers conocidos a sus índices."""
        headers = [
            "Número Factura",
            "Vlr. Subsidiado",
            "Vlr. Procedimiento",
            "Tipo Procedimiento",
        ]

        indices, _ = _get_column_indices(headers)

        assert indices["numero_factura"] == 0
        assert indices["vlr_subsidiado"] == 1
        assert indices["vlr_procedimiento"] == 2
        assert indices["tipo_procedimiento"] == 3

    def test_headers_no_encontrados_son_none(self) -> None:
        """Headers no encontrados deben ser None."""
        headers = ["Columna Rara", "Otra Columna"]

        indices, _ = _get_column_indices(headers)

        assert indices["numero_factura"] is None
        assert indices["vlr_subsidiado"] is None

    def test_requiere_coincidencia_exacta(self) -> None:
        """Requiere coincidencia EXACTA, no infiere."""
        headers = ["Número Factura", "Nº Identificación"]

        indices, _ = _get_column_indices(headers)

        assert indices["numero_factura"] == 0
        assert indices["identificacion"] == 1


class TestDetectDecimals:
    """Tests para _detect_decimals."""

    def test_detecta_facturas_con_decimales(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar facturas con valores decimales."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", vlr_sub=1000.50)  # Decimal
        add_invoice_row(ws, 3, "FAC-002", vlr_sub=1000.00)  # Entero
        add_invoice_row(ws, 4, "FAC-003", vlr_proc=500.25)  # Decimal en vlr_proc

        headers = [ws.cell(row=1, column=c).value for c in range(1, 10)]
        indices, _ = _get_column_indices(headers)

        result = _detect_decimals(ws, indices)

        assert len(result) == 2
        facturas = [r["factura"] for r in result]
        assert "FAC-001" in facturas
        assert "FAC-002" not in facturas
        assert "FAC-003" in facturas

    def test_no_duplica_facturas(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """No debe duplicar facturas con decimales en ambos campos."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", vlr_sub=1000.50, vlr_proc=500.25)

        headers = [ws.cell(row=1, column=c).value for c in range(1, 10)]
        indices, _ = _get_column_indices(headers)

        result = _detect_decimals(ws, indices)

        assert len(result) == 1
        assert result[0]["factura"] == "FAC-001"


class TestDetectDobleTipoProcedimiento:
    """Tests para _detect_doble_tipo_procedimiento."""

    def test_detecta_factura_con_multiples_tipos(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar facturas con más de un tipo de procedimiento."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", tipo_proc="Consultas")
        add_invoice_row(ws, 3, "FAC-001", tipo_proc="Procedimientos")
        add_invoice_row(ws, 4, "FAC-002", tipo_proc="Consultas")
        add_invoice_row(ws, 5, "FAC-002", tipo_proc="Consultas")

        headers = [ws.cell(row=1, column=c).value for c in range(1, 10)]
        indices, _ = _get_column_indices(headers)

        result = _detect_doble_tipo_procedimiento(ws, indices)

        facturas = [r["factura"] for r in result]
        assert "FAC-001" in facturas
        assert "FAC-002" not in facturas


class TestDetectRutaDuplicada:
    """Tests para _detect_ruta_duplicada."""

    def test_detecta_paciente_con_multiples_facturas_pyp(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar pacientes con >= 3 facturas en PyP."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", identificacion="PAC-001", convenio=CONVENIO_PYP)
        add_invoice_row(ws, 3, "FAC-002", identificacion="PAC-001", convenio=CONVENIO_PYP)
        add_invoice_row(ws, 4, "FAC-003", identificacion="PAC-001", convenio=CONVENIO_PYP)
        add_invoice_row(ws, 5, "FAC-004", identificacion="PAC-002", convenio=CONVENIO_PYP)
        add_invoice_row(ws, 6, "FAC-005", identificacion="PAC-002", convenio=CONVENIO_PYP)

        headers = [ws.cell(row=1, column=c).value for c in range(1, 10)]
        indices, _ = _get_column_indices(headers)

        result = _detect_ruta_duplicada(ws, indices)

        identificaciones = [r["identificacion"] for r in result]
        assert "PAC-001" in identificaciones
        assert "PAC-002" not in identificaciones

    def test_ignora_facturas_no_pyp(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe ignorar facturas con convenio diferente a PyP."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", identificacion="PAC-001", convenio=CONVENIO_ASISTENCIAL)
        add_invoice_row(ws, 3, "FAC-002", identificacion="PAC-001", convenio=CONVENIO_ASISTENCIAL)
        add_invoice_row(ws, 4, "FAC-003", identificacion="PAC-001", convenio=CONVENIO_ASISTENCIAL)

        headers = [ws.cell(row=1, column=c).value for c in range(1, 10)]
        indices, _ = _get_column_indices(headers)

        result = _detect_ruta_duplicada(ws, indices)

        assert len(result) == 0


class TestDetectCantidadesAnomalas:
    """Tests para _detect_cantidades_anomalas."""

    def test_detecta_consultas_con_cantidad_mayor_igual_2(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar consultas con cantidad >= 2."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", tipo_proc="Consultas", cantidad=2)
        add_invoice_row(ws, 3, "FAC-002", tipo_proc="Consultas", cantidad=1)

        headers = [ws.cell(row=1, column=c).value for c in range(1, 10)]
        indices, _ = _get_column_indices(headers)

        result = _detect_cantidades_anomalas(ws, indices)

        facturas = [r["factura"] for r in result]
        assert "FAC-001" in facturas
        assert "FAC-002" not in facturas

    def test_detecta_cantidad_mayor_10(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar cualquier cantidad > 10."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", tipo_proc="Otros", cantidad=11)
        add_invoice_row(ws, 3, "FAC-002", tipo_proc="Otros", cantidad=10)

        headers = [ws.cell(row=1, column=c).value for c in range(1, 10)]
        indices, _ = _get_column_indices(headers)

        result = _detect_cantidades_anomalas(ws, indices)

        facturas = [r["factura"] for r in result]
        assert "FAC-001" in facturas
        assert "FAC-002" not in facturas

    def test_detecta_pyp_con_cantidad_mayor_igual_3(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar PyP con cantidad >= 3."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", tipo_proc="Procedimientos", convenio=CONVENIO_PYP, cantidad=3)
        add_invoice_row(ws, 3, "FAC-002", tipo_proc="Procedimientos", convenio=CONVENIO_PYP, cantidad=2)

        headers = [ws.cell(row=1, column=c).value for c in range(1, 10)]
        indices, _ = _get_column_indices(headers)

        result = _detect_cantidades_anomalas(ws, indices)

        facturas = [r["factura"] for r in result]
        assert "FAC-001" in facturas
        assert "FAC-002" not in facturas


class TestWriteColumn:
    """Tests para _write_column."""

    def test_escribe_valores_en_columna(self) -> None:
        """Debe escribir valores en una columna empezando en la fila indicada."""
        wb = Workbook()
        ws = wb.active
        values = ["A", "B", "C"]

        _write_column(ws, 2, values, start_row=3)

        assert ws.cell(row=3, column=2).value == "A"
        assert ws.cell(row=4, column=2).value == "B"
        assert ws.cell(row=5, column=2).value == "C"


class TestBuildUrgenciasNormalizedRows:
    """Tests para _build_urgencias_normalized_rows."""

    def test_centros_de_costo(self) -> None:
        """Debe normalizar centros de costo."""
        rows = _build_urgencias_normalized_rows(
            problemas_centros=[{
                "factura": "F001",
                "codigo": "890405",
                "procedimiento": "CONSULTA",
                "centro_actual": "URGENCIAS",
                "centro_deberia": "APOYO DIAGNOSTICO",
            }],
            problemas_ide_contrato=[],
            problemas_cups_equivalentes=[],
            mal_capitado=[],
            cantidades_urgencias=[],
            cantidades_hospitalizacion=[],
            responsable_cierra={"F001": "JUAN"},
        )

        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "Centros de Costo"
        assert r["factura"] == "F001"
        assert r["responsable_cierra"] == "JUAN"
        assert r["descripcion"] == "Centro de costo debería ser APOYO DIAGNOSTICO"
        assert r["procedimiento"] == "890405 - CONSULTA"
        assert r["detalle"] == "URGENCIAS"

    def test_ide_contrato(self) -> None:
        """Debe normalizar IDE Contrato."""
        rows = _build_urgencias_normalized_rows(
            problemas_centros=[],
            problemas_ide_contrato=[{
                "factura": "F002",
                "codigo": "861801",
                "procedimiento": "CONSULTA ENFERMERIA",
                "ide_contrato_actual": "900",
                "ide_contrato_deberia": "977",
            }],
            problemas_cups_equivalentes=[],
            mal_capitado=[],
            cantidades_urgencias=[],
            cantidades_hospitalizacion=[],
            responsable_cierra={},
        )

        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "IDE Contrato"
        assert r["factura"] == "F002"
        assert r["descripcion"] == "IDE Contrato debería ser 977"
        assert r["procedimiento"] == "861801 - CONSULTA ENFERMERIA"
        assert r["detalle"] == "900"

    def test_cantidades_urgencias(self) -> None:
        """Debe normalizar cantidades de Urgencias."""
        rows = _build_urgencias_normalized_rows(
            problemas_centros=[],
            problemas_ide_contrato=[],
            problemas_cups_equivalentes=[],
            mal_capitado=[],
            cantidades_urgencias=[{
                "factura": "F003",
                "codigo": "890601",
                "procedimiento": "MANEJO INTRAHOSP",
                "cantidad": 3,
            }],
            cantidades_hospitalizacion=[],
            responsable_cierra={},
        )

        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "Cantidades"
        assert r["factura"] == "F003"
        assert r["descripcion"] == "Cantidad 3 debe ser ≤ 1 en Urgencias"
        assert r["procedimiento"] == "890601 - MANEJO INTRAHOSP"
        assert r["detalle"] == "3"


class TestCreateRevisionSheetOdontologia:
    """Tests para create_revision_sheet con área Odontología."""

    def test_crea_hoja_revision(self, workbook_with_invoice_data: Workbook) -> None:
        """Debe crear hoja Revision con headers correctos."""
        wb = workbook_with_invoice_data
        ws = wb.active
        add_invoice_row(ws, 2, "FAC-001")

        result = create_revision_sheet(wb, ws)

        assert result["rule"] == "create_revision_sheet"
        assert result["sheet"] == REVISION_SHEET
        assert REVISION_SHEET in wb.sheetnames

    def test_headers_de_odontologia(self, workbook_with_invoice_data: Workbook) -> None:
        """Headers deben ser los de Odontología."""
        wb = workbook_with_invoice_data
        ws = wb.active
        add_invoice_row(ws, 2, "FAC-001")

        result = create_revision_sheet(wb, ws)

        assert result["headers"] == list(REVISION_HEADERS.values())

    def test_resultado_tiene_key_problemas(self, workbook_with_invoice_data: Workbook) -> None:
        """Debe retornar dict con key problemas."""
        wb = workbook_with_invoice_data
        ws = wb.active
        add_invoice_row(ws, 2, "FAC-001")

        result = create_revision_sheet(wb, ws)

        assert "problemas" in result
