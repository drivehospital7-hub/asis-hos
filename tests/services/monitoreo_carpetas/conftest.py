"""Shared fixtures and helpers for monitoreo_carpetas tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from app.services.monitoreo_carpetas import InvoiceRecord


@pytest.fixture
def temp_scan_root() -> Generator[Path, None, None]:
    """Creates a multi-level directory tree simulating network roots.

    Structure (depth ~4 from root):
        tmp/
        ├── 0 FACTURAS CAPITA OK - Juan/   → Verificada
        │   └── company_A/
        │       ├── FEV12345/              → invoice folder (non-empty)
        │       │   └── dummy.txt
        │       ├── CAP001_ABC002/          → invoice folder (non-empty)
        │       │   └── dummy.txt
        │       └── CRC_01/                → non-invoice (pre-filter skip)
        │           └── dummy.txt
        ├── CORREGIR - Carlos/             → Por corregir
        │   └── company_B/
        │       └── FEV67890/              → invoice folder (non-empty)
        │           └── dummy.txt
        └── PENDIENTE - Luis/              → En revisión
            └── company_C/
                └── HAU_02/                → non-invoice (pre-filter skip)
                    └── dummy.txt
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Juan - Verificada (FACTURAS CAPITA OK)
        juan = root / "0 FACTURAS CAPITA OK - Juan"
        juan_company = juan / "company_A"
        juan_company.mkdir(parents=True)
        (juan_company / "FEV12345").mkdir()
        (juan_company / "FEV12345" / "dummy.txt").write_text("dummy")
        (juan_company / "CAP001_ABC002").mkdir()
        (juan_company / "CAP001_ABC002" / "dummy.txt").write_text("dummy")
        # Non-invoice folder — should be skipped by pre-filter
        (juan_company / "CRC_01").mkdir()
        (juan_company / "CRC_01" / "dummy.txt").write_text("dummy")

        # Carlos - Por corregir
        carlos = root / "CORREGIR - Carlos"
        carlos_company = carlos / "company_B"
        carlos_company.mkdir(parents=True)
        (carlos_company / "FEV67890").mkdir()
        (carlos_company / "FEV67890" / "dummy.txt").write_text("dummy")

        # Luis - En revisión (no keyword match) — non-invoice + empty invoice folder
        luis = root / "PENDIENTE - Luis"
        luis_company = luis / "company_C"
        luis_company.mkdir(parents=True)
        (luis_company / "HAU_02").mkdir()
        (luis_company / "HAU_02" / "dummy.txt").write_text("dummy")
        # Empty FEV folder — should be flagged as empty
        (luis_company / "FEV99999").mkdir()

        yield root


@pytest.fixture
def sample_invoice_records() -> list[InvoiceRecord]:
    """Returns a list of sample InvoiceRecord instances for testing."""
    return [
        InvoiceRecord(
            filename="FEV12345.pdf",
            facturador="0 FACTURAS CAPITA OK - Juan",
            full_path="/roots/0 FACTURAS CAPITA OK - Juan/FEV12345.pdf",
            status="Verificada",
            invoice_type="FEV",
            invoice_code="FEV12345",
        ),
        InvoiceRecord(
            filename="CAP001_ABC002.pdf",
            facturador="0 FACTURAS CAPITA OK - Juan",
            full_path="/roots/0 FACTURAS CAPITA OK - Juan/CAP001_ABC002.pdf",
            status="Verificada",
            invoice_type="CAP",
            invoice_code="CAP001_ABC002",
        ),
        InvoiceRecord(
            filename="FEV67890.pdf",
            facturador="Carlos",
            full_path="/roots/CORREGIR - Carlos/FEV67890.pdf",
            status="Por corregir",
            invoice_type="FEV",
            invoice_code="FEV67890",
        ),
        InvoiceRecord(
            filename="FEV99999.pdf",
            facturador="Maria",
            full_path="/roots/0 LISTAS PARA PASAR M - Maria/FEV99999.pdf",
            status="Verificada",
            invoice_type="FEV",
            invoice_code="FEV99999",
        ),
    ]
