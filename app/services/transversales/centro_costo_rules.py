"""Reglas comunes de centro de costo (transversales a todos los tipos de factura).

Aplica reglas 1, 1-REVERSE, 2, 2-REVERSE, 3, 3-REVERSE, 4, 4-REVERSE,
8, 9, 9-REVERSE y validación de centro de costo inválido.
Las reglas específicas de cada tipo de factura se aplican en los wrappers.
"""

from __future__ import annotations

from typing import Any

from app.constants import (
    CENTRO_COSTO_APOYO_DIAGNOSTICO,
    CENTRO_COSTO_FARMACIA,
    CENTRO_COSTO_HOSPITALIZACION_ESTANCIA,
    CENTRO_COSTO_PYP_URGENCIAS,
    CENTRO_COSTO_QUIROFANO_URGENCIAS,
    CENTRO_COSTO_TRASLADOS,
    CENTROS_COSTO_VALIDOS_URGENCIAS,
    CODIGOS_EXCEPTUADOS,
    CODIGOS_HOSPITALIZACION_ESTANCIA,
    CODIGOS_PYP_URGENCIAS,
    CODIGOS_QUIROFANO_URGENCIAS,
    CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO,
    CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS,
    LABORATORIO_NO,
    VALOR_TARIFARIO_FARMACIA,
)


def apply_common_centro_costo_rules(
    *,
    centro_costo_str: str,
    codigo_str: str,
    codigo_excluir: str,
    laboratorio_str: str,
    tarifario_str: str,
    codigo_entidad_str: str,
    factura_str: str,
    proc_str: str,
    centros_validos: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Aplica las reglas de centro de costo comunes a todos los tipos de factura.

    Args:
        centro_costo_str: Valor normalizado de la columna Centro Costo
        codigo_str: Valor normalizado de Código Tipo Procedimiento
        codigo_excluir: Valor normalizado del código (para comparar con listas)
        laboratorio_str: Valor normalizado de Laboratorio
        tarifario_str: Valor normalizado de Tarifario
        codigo_entidad_str: Valor normalizado de Cód Entidad Cobrar
        factura_str: Número de factura normalizado
        proc_str: Procedimiento normalizado
        centros_validos: Conjunto de centros de costo válidos (default: CENTROS_COSTO_VALIDOS_URGENCIAS)

    Returns:
        Lista de dicts con keys: factura, tipo_factura, centro_actual,
        centro_deberia, codigo, procedimiento, prioridad, regla
    """
    if not centro_costo_str:
        return []

    if centros_validos is None:
        centros_validos = CENTROS_COSTO_VALIDOS_URGENCIAS

    errors: list[dict[str, Any]] = []

    def _error(centro_deberia: str, prioridad: int = 1, regla: str = "") -> None:
        errors.append({
            "factura": factura_str,
            "tipo_factura": "",
            "centro_actual": centro_costo_str,
            "centro_deberia": centro_deberia,
            "codigo": codigo_excluir,
            "procedimiento": proc_str,
            "prioridad": prioridad,
            "regla": regla,
        })

    # --- Centro de costo inválido ---
    if centro_costo_str not in centros_validos:
        _error("Centro de costo no válido para Urgencias", prioridad=1, regla="CENTRO_INVALIDO")

    # --- Regla 9: Tarifario farmacia → Centro debe ser FARMACIA ---
    if tarifario_str == VALOR_TARIFARIO_FARMACIA:
        if centro_costo_str != CENTRO_COSTO_FARMACIA:
            _error(CENTRO_COSTO_FARMACIA, regla="REGLA9")

    # --- Regla 1: Código=02 + Lab=No → Centro APOYO DIAGNÓSTICO ---
    regla_1_activa = (
        codigo_str == CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO
        and laboratorio_str == LABORATORIO_NO
    )
    es_exceptuado = codigo_excluir in CODIGOS_EXCEPTUADOS
    if regla_1_activa and not es_exceptuado and centro_costo_str != CENTRO_COSTO_APOYO_DIAGNOSTICO:
        _error(CENTRO_COSTO_APOYO_DIAGNOSTICO)

    # --- Regla 1 REVERSE: Centro=APOYO DIAGNÓSTICO → Código=02 + Lab=No ---
    if centro_costo_str == CENTRO_COSTO_APOYO_DIAGNOSTICO:
        if codigo_str != CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO or laboratorio_str != LABORATORIO_NO:
            _error(
                f"Código={CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO} + Laboratorio={LABORATORIO_NO}",
                regla="REVERSE1",
            )

    # --- Regla 2: Código=14 → Centro TRASLADOS ---
    if codigo_str == CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS:
        if centro_costo_str != CENTRO_COSTO_TRASLADOS:
            _error(CENTRO_COSTO_TRASLADOS)

    # --- Regla 2 REVERSE: Centro=TRASLADOS → Código debe ser 14 ---
    if centro_costo_str == CENTRO_COSTO_TRASLADOS:
        if codigo_str != CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS:
            _error(f"Código={CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS}", regla="REVERSE2")

    # --- Regla 3: Código en PYP → Centro PYP ---
    if codigo_excluir in CODIGOS_PYP_URGENCIAS:
        if centro_costo_str != CENTRO_COSTO_PYP_URGENCIAS:
            _error(CENTRO_COSTO_PYP_URGENCIAS)

    # --- Regla 3 REVERSE: Centro=PYP → Código debe ser PYP ---
    if centro_costo_str == CENTRO_COSTO_PYP_URGENCIAS:
        if codigo_excluir not in CODIGOS_PYP_URGENCIAS:
            _error("Procedimiento con mal uso de centro de costo PYP", regla="REVERSE3")

    # --- Regla 4: Código en QUIRÓFANOS → Centro QUIRÓFANOS ---
    if codigo_excluir in CODIGOS_QUIROFANO_URGENCIAS:
        if centro_costo_str != CENTRO_COSTO_QUIROFANO_URGENCIAS:
            _error(CENTRO_COSTO_QUIROFANO_URGENCIAS)

    # --- Regla 4 REVERSE: Centro=QUIRÓFANOS → Código QUIRÓFANOS ---
    if centro_costo_str == CENTRO_COSTO_QUIROFANO_URGENCIAS:
        if codigo_excluir not in CODIGOS_QUIROFANO_URGENCIAS:
            _error("Procedimiento con mal uso de centro de costo QUIRÓFANOS", regla="REVERSE4")

    # --- Regla 9 REVERSE: Centro=FARMACIA → Tarifario farmacia ---
    if centro_costo_str == CENTRO_COSTO_FARMACIA:
        if tarifario_str != VALOR_TARIFARIO_FARMACIA:
            _error(f"Tarifario debe ser {VALOR_TARIFARIO_FARMACIA}", regla="REVERSE9")

    # --- Regla 8: Código 890601H/39133 → Centro HOSPITALIZACIÓN ESTANCIA ---
    if codigo_excluir in CODIGOS_HOSPITALIZACION_ESTANCIA:
        if centro_costo_str != CENTRO_COSTO_HOSPITALIZACION_ESTANCIA:
            _error(CENTRO_COSTO_HOSPITALIZACION_ESTANCIA)

    return errors
