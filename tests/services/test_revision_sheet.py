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
    _detect_convenio_procedimiento,
    _detect_cantidades_anomalas,
    _write_column,
    create_revision_sheet,
    REVISION_HEADERS,
)
from app.constants import (
    CONVENIO_ASISTENCIAL,
    CONVENIO_PYP,
    REVISION_SHEET,
    TARGET_PROCEDURES,
)


@pytest.fixture
def workbook_with_invoice_data() -> Workbook:
    """Crea un workbook con datos de facturas para pruebas."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    
    # Headers
    headers = [
        "Número Factura",
        "Vlr. Subsidiado",
        "Vlr. Procedimiento",
        "Tipo Procedimiento",
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
    ws.cell(row=row, column=5, value=procedimiento)
    ws.cell(row=row, column=6, value=identificacion)
    ws.cell(row=row, column=7, value=convenio)
    ws.cell(row=row, column=8, value=cantidad)


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
        assert _normalize_invoice("   ") is None


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
        
        indices = _get_column_indices(headers)
        
        assert indices["numero_factura"] == 0
        assert indices["vlr_subsidiado"] == 1
        assert indices["vlr_procedimiento"] == 2
        assert indices["tipo_procedimiento"] == 3

    def test_headers_no_encontrados_son_none(self) -> None:
        """Headers no encontrados deben ser None."""
        headers = ["Columna Rara", "Otra Columna"]
        
        indices = _get_column_indices(headers)
        
        assert indices["numero_factura"] is None
        assert indices["vlr_subsidiado"] is None

    def test_reconoce_variantes_de_headers(self) -> None:
        """Debe reconocer variantes de nombres de columnas."""
        headers = ["numero factura", "nº identificación"]
        
        indices = _get_column_indices(headers)
        
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
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_decimals(ws, indices)
        
        assert "FAC-001" in result
        assert "FAC-002" not in result
        assert "FAC-003" in result

    def test_no_duplica_facturas(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """No debe duplicar facturas con decimales en ambos campos."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", vlr_sub=1000.50, vlr_proc=500.25)
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_decimals(ws, indices)
        
        assert result.count("FAC-001") == 1


class TestDetectDobleTipoProcedimiento:
    """Tests para _detect_doble_tipo_procedimiento."""

    def test_detecta_factura_con_multiples_tipos(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar facturas con más de un tipo de procedimiento."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", tipo_proc="Consultas")
        add_invoice_row(ws, 3, "FAC-001", tipo_proc="Procedimientos")  # Mismo FAC, otro tipo
        add_invoice_row(ws, 4, "FAC-002", tipo_proc="Consultas")
        add_invoice_row(ws, 5, "FAC-002", tipo_proc="Consultas")  # Mismo tipo
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_doble_tipo_procedimiento(ws, indices)
        
        assert "FAC-001" in result
        assert "FAC-002" not in result


class TestDetectRutaDuplicada:
    """Tests para _detect_ruta_duplicada."""

    def test_detecta_paciente_con_multiples_facturas_pyp(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar pacientes con >= 3 facturas en PyP."""
        ws = workbook_with_invoice_data.active
        # Paciente con 3 facturas PyP
        add_invoice_row(ws, 2, "FAC-001", identificacion="PAC-001", convenio=CONVENIO_PYP)
        add_invoice_row(ws, 3, "FAC-002", identificacion="PAC-001", convenio=CONVENIO_PYP)
        add_invoice_row(ws, 4, "FAC-003", identificacion="PAC-001", convenio=CONVENIO_PYP)
        # Paciente con 2 facturas PyP (no debe aparecer)
        add_invoice_row(ws, 5, "FAC-004", identificacion="PAC-002", convenio=CONVENIO_PYP)
        add_invoice_row(ws, 6, "FAC-005", identificacion="PAC-002", convenio=CONVENIO_PYP)
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_ruta_duplicada(ws, indices)
        
        assert "PAC-001" in result
        assert "PAC-002" not in result

    def test_ignora_facturas_no_pyp(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe ignorar facturas con convenio diferente a PyP."""
        ws = workbook_with_invoice_data.active
        # 3 facturas Asistencial (no deben contar)
        add_invoice_row(ws, 2, "FAC-001", identificacion="PAC-001", convenio=CONVENIO_ASISTENCIAL)
        add_invoice_row(ws, 3, "FAC-002", identificacion="PAC-001", convenio=CONVENIO_ASISTENCIAL)
        add_invoice_row(ws, 4, "FAC-003", identificacion="PAC-001", convenio=CONVENIO_ASISTENCIAL)
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_ruta_duplicada(ws, indices)
        
        assert "PAC-001" not in result


class TestDetectConvenioProcedimiento:
    """Tests para _detect_convenio_procedimiento."""

    def test_detecta_asistencial_con_procedimiento_pyp(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar facturas Asistencial con procedimientos de PyP."""
        ws = workbook_with_invoice_data.active
        proc_pyp = list(TARGET_PROCEDURES)[0]  # Un procedimiento PyP
        add_invoice_row(
            ws, 2, "FAC-001",
            convenio=CONVENIO_ASISTENCIAL,
            procedimiento=proc_pyp,
        )
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_convenio_procedimiento(ws, indices)
        
        assert "FAC-001" in result

    def test_detecta_pyp_con_procedimiento_no_pyp(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar facturas PyP con procedimientos no PyP."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(
            ws, 2, "FAC-002",
            convenio=CONVENIO_PYP,
            procedimiento="Procedimiento NO PyP",
        )
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_convenio_procedimiento(ws, indices)
        
        assert "FAC-002" in result

    def test_no_detecta_combinacion_correcta(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """No debe detectar si convenio y procedimiento coinciden."""
        ws = workbook_with_invoice_data.active
        proc_pyp = list(TARGET_PROCEDURES)[0]
        add_invoice_row(
            ws, 2, "FAC-003",
            convenio=CONVENIO_PYP,
            procedimiento=proc_pyp,  # PyP con proc PyP = OK
        )
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_convenio_procedimiento(ws, indices)
        
        assert "FAC-003" not in result


class TestDetectCantidadesAnomalas:
    """Tests para _detect_cantidades_anomalas."""

    def test_detecta_consultas_con_cantidad_mayor_igual_2(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar consultas con cantidad >= 2."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", tipo_proc="Consultas", cantidad=2)
        add_invoice_row(ws, 3, "FAC-002", tipo_proc="Consultas", cantidad=1)
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_cantidades_anomalas(ws, indices)
        
        assert "FAC-001" in result
        assert "FAC-002" not in result

    def test_detecta_cantidad_mayor_10(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar cualquier cantidad > 10."""
        ws = workbook_with_invoice_data.active
        add_invoice_row(ws, 2, "FAC-001", tipo_proc="Otros", cantidad=11)
        add_invoice_row(ws, 3, "FAC-002", tipo_proc="Otros", cantidad=10)
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_cantidades_anomalas(ws, indices)
        
        assert "FAC-001" in result
        assert "FAC-002" not in result

    def test_detecta_pyp_con_cantidad_mayor_igual_3(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe detectar facturas PyP con cantidad >= 3."""
        ws = workbook_with_invoice_data.active
        # Usar tipo_proc diferente a "Consultas" para evitar que se active esa regla
        add_invoice_row(ws, 2, "FAC-001", convenio=CONVENIO_PYP, cantidad=3, tipo_proc="Procedimientos")
        add_invoice_row(ws, 3, "FAC-002", convenio=CONVENIO_PYP, cantidad=2, tipo_proc="Procedimientos")
        
        headers = [ws.cell(row=1, column=c).value for c in range(1, 9)]
        indices = _get_column_indices(headers)
        
        result = _detect_cantidades_anomalas(ws, indices)
        
        assert "FAC-001" in result
        assert "FAC-002" not in result


class TestWriteColumn:
    """Tests para _write_column."""

    def test_escribe_valores_en_columna(self) -> None:
        """Debe escribir valores en la columna especificada."""
        wb = Workbook()
        ws = wb.active
        
        valores = ["A", "B", "C"]
        _write_column(ws, column=1, values=valores, start_row=2)
        
        assert ws.cell(row=2, column=1).value == "A"
        assert ws.cell(row=3, column=1).value == "B"
        assert ws.cell(row=4, column=1).value == "C"

    def test_lista_vacia_no_escribe_nada(self) -> None:
        """Lista vacía no debe escribir nada."""
        wb = Workbook()
        ws = wb.active
        
        _write_column(ws, column=1, values=[])
        
        assert ws.cell(row=2, column=1).value is None


class TestCreateRevisionSheet:
    """Tests para create_revision_sheet."""

    def test_crea_hoja_con_headers(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe crear hoja Revision con los headers correctos."""
        wb = workbook_with_invoice_data
        
        result = create_revision_sheet(wb)
        
        assert REVISION_SHEET in wb.sheetnames
        revision_sheet = wb[REVISION_SHEET]
        
        for col, header in REVISION_HEADERS.items():
            assert revision_sheet.cell(row=1, column=col).value == header

    def test_retorna_info_de_problemas_encontrados(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe retornar dict con información de problemas encontrados."""
        wb = workbook_with_invoice_data
        ws = wb.active
        add_invoice_row(ws, 2, "FAC-001", vlr_sub=1000.50)  # Decimal
        
        result = create_revision_sheet(wb)
        
        assert result["rule"] == "create_revision_sheet"
        assert result["sheet"] == REVISION_SHEET
        assert "decimal_invoices_found" in result
        assert "doble_tipo_invoices_found" in result
        assert "ruta_duplicada_found" in result
        assert "convenio_de_procedimiento_found" in result
        assert "cantidades_found" in result

    def test_escribe_facturas_con_problemas_en_columnas(
        self, workbook_with_invoice_data: Workbook
    ) -> None:
        """Debe escribir facturas con problemas en las columnas correspondientes."""
        wb = workbook_with_invoice_data
        ws = wb.active
        add_invoice_row(ws, 2, "FAC-DECIMAL", vlr_sub=100.50)
        
        create_revision_sheet(wb)
        
        revision_sheet = wb[REVISION_SHEET]
        # Columna 1 = Decimales
        assert revision_sheet.cell(row=2, column=1).value == "FAC-DECIMAL"
