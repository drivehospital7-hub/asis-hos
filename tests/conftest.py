"""Configuración global de pytest para el proyecto control_system."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from openpyxl import Workbook

from app import create_app


@pytest.fixture
def app_client():
    """Flask test client usando create_app()."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Directorio temporal para archivos de salida."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_excel_file(temp_output_dir: Path) -> Generator[Path, None, None]:
    """Crea un archivo Excel temporal con datos de ejemplo."""
    file_path = temp_output_dir / "sample.xlsx"
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    
    # Headers en fila 1
    headers = ["NUMERO_FACTURA", "VALOR", "FECHA", "CONVENIO"]
    for col, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=header)
    
    # Datos de ejemplo en filas 2-4
    sample_data = [
        ["FAC-001", 15000.50, "2024-01-15", "ODONTOLOGIA"],
        ["FAC-002", 22300.00, "2024-01-16", "ODONTOLOGIA"],
        ["FAC-003", 8750.25, "2024-01-17", "GENERAL"],
    ]
    for row_idx, row_data in enumerate(sample_data, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    wb.save(file_path)
    yield file_path


@pytest.fixture
def empty_excel_file(temp_output_dir: Path) -> Generator[Path, None, None]:
    """Crea un archivo Excel temporal sin columnas (hoja vacía)."""
    file_path = temp_output_dir / "empty.xlsx"
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Vacia"
    # No agregamos nada - hoja completamente vacía
    
    wb.save(file_path)
    yield file_path
