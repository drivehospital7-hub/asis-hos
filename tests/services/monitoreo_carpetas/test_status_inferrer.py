"""Tests for app/services/monitoreo_carpetas/status_inferrer.py."""

from __future__ import annotations

import pytest

from app.services.monitoreo_carpetas.status_inferrer import infer_status


class TestInferStatus:
    """Tests for infer_status()."""

    def test_verificada_facturas_capita_ok(self) -> None:
        """infer_status returns Verificada for folder names containing FACTURAS CAPITA OK."""
        assert infer_status("0 FACTURAS CAPITA OK") == "Verificada"

    def test_verificada_listas_para_pasar(self) -> None:
        """infer_status returns Verificada for folder names containing LISTAS PARA PASAR."""
        assert infer_status("0 LISTAS PARA PASAR M") == "Verificada"

    def test_por_corregir_corregir(self) -> None:
        """infer_status returns Por corregir for folder names containing CORREGIR."""
        assert infer_status("CORREGIR - Carlos") == "Por corregir"

    def test_por_corregir_correccion(self) -> None:
        """infer_status returns Por corregir for folder names containing CORRECCION."""
        assert infer_status("CORRECCION - Ana") == "Por corregir"

    def test_default_en_revision(self) -> None:
        """infer_status returns En revisión for folder names with no keyword match."""
        assert infer_status("PENDIENTE - Luis") == "En revisión"

    def test_default_unknown_name(self) -> None:
        """infer_status returns En revisión for completely unrecognized folder names."""
        assert infer_status("NUEVOS - Pedro") == "En revisión"

    def test_case_insensitive(self) -> None:
        """infer_status should be case-insensitive for keyword matching."""
        assert infer_status("0 facturas capita ok") == "Verificada"
        assert infer_status("0 listas para pasar m") == "Verificada"
        assert infer_status("Corregir - Carlos") == "Por corregir"

    def test_keyword_in_middle_of_name(self) -> None:
        """infer_status detects keywords even when not at the start."""
        assert infer_status("ACTAS LISTAS PARA PASAR MAYO") == "Verificada"
        assert infer_status("ARCHIVOS CORREGIR MAYO") == "Por corregir"

    def test_empty_folder_name_defaults(self) -> None:
        """infer_status returns En revisión for empty string."""
        assert infer_status("") == "En revisión"
