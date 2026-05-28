"""Mapping de reglas IDE Contrato para Intramural.

TIPO: Data/config, NO código procedural.
Cada regla es un dict con:
- codigo: Código CUPS a validar
- entidad: Cód Entidad Cobrar a validar
- type: tipo de regla
- expected: valor(es) esperado(s) de IDE Contrato
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# Reglas EXACTAS: (codigo, entidad) → IDE único esperado
# =============================================================================

IDE_SIMPLE_RULES: list[dict[str, Any]] = [
    # --- EPSS41 (COMENTADO) ---
    # {"codigo": "906340", "entidad": "EPSS41", "type": "exact", "expected": "957", "note": "906340 + EPSS41 -> IDE 957"},
    # {"codigo": "906127", "entidad": "EPSS41", "type": "exact", "expected": "958", "note": "Toxoplasma IGG + EPSS41 -> IDE 958"},
    # {"codigo": "906129", "entidad": "EPSS41", "type": "exact", "expected": "958", "note": "Toxoplasma IGM + EPSS41 -> IDE 958"},
    # {"codigo": "906205", "entidad": "EPSS41", "type": "exact", "expected": "958", "note": "CMV IGG + EPSS41 -> IDE 958"},
    # {"codigo": "906206", "entidad": "EPSS41", "type": "exact", "expected": "958", "note": "CMV IGM + EPSS41 -> IDE 958"},
    # {"codigo": "906131", "entidad": "EPSS41", "type": "exact", "expected": "958", "note": "Trypanosoma IGG + EPSS41 -> IDE 958"},
    # {"codigo": "990211", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Consejeria VIH + EPSS41 -> IDE 955"},
    # {"codigo": "897011", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Monitoria Fetal + EPSS41 -> IDE 955"},
    # {"codigo": "995201", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Otras Vac PAI SOD + EPSS41 -> IDE 955"},
    # {"codigo": "993513", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Vacuna VPH + EPSS41 -> IDE 955"},
    # {"codigo": "993520", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Doble Viral SR + EPSS41 -> IDE 955"},
    # {"codigo": "993106", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Vacuna Neumococo + EPSS41 -> IDE 955"},
    # {"codigo": "993502", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Vacuna Hepatitis A + EPSS41 -> IDE 955"},
    # {"codigo": "993503", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Vacuna Hepatitis B + EPSS41 -> IDE 955"},
    # {"codigo": "993505", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Vacuna Rabia + EPSS41 -> IDE 955"},
    # {"codigo": "993512", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Vacuna Rotavirus + EPSS41 -> IDE 955"},
    # {"codigo": "993102", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "BCG + EPSS41 -> IDE 955"},
    # {"codigo": "993509", "entidad": "EPSS41", "type": "exact", "expected": "955", "note": "Vacuna Varicela + EPSS41 -> IDE 955"},
    # --- EPS037 ---
    {"codigo": "906340", "entidad": "EPS037", "type": "exact", "expected": "960", "note": "906340 + EPS037 -> IDE 960"},
    # --- EPS037 + EXAMENES PYM EVENTO / PYM INTRAMURAL -> IDE 961 ---
    {"codigo": "906127", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Toxoplasma IGG + EPS037 -> IDE 961"},
    {"codigo": "906129", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Toxoplasma IGM + EPS037 -> IDE 961"},
    {"codigo": "906205", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "CMV IGG + EPS037 -> IDE 961"},
    {"codigo": "906206", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "CMV IGM + EPS037 -> IDE 961"},
    {"codigo": "906241", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Rubeola IGG + EPS037 -> IDE 961"},
    {"codigo": "906131", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Trypanosoma IGG + EPS037 -> IDE 961"},
    {"codigo": "990211", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Consejeria VIH + EPS037 -> IDE 961"},
    {"codigo": "897011", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Monitoria Fetal + EPS037 -> IDE 961"},
    {"codigo": "995201", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Otras Vac PAI SOD + EPS037 -> IDE 961"},
    {"codigo": "993513", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Vacuna VPH + EPS037 -> IDE 961"},
    {"codigo": "993520", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Doble Viral SR + EPS037 -> IDE 961"},
    {"codigo": "993106", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Vacuna Neumococo + EPS037 -> IDE 961"},
    {"codigo": "993502", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Vacuna Hepatitis A + EPS037 -> IDE 961"},
    {"codigo": "993503", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Vacuna Hepatitis B + EPS037 -> IDE 961"},
    {"codigo": "993505", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Vacuna Rabia + EPS037 -> IDE 961"},
    {"codigo": "993512", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Vacuna Rotavirus + EPS037 -> IDE 961"},
    {"codigo": "993102", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "BCG + EPS037 -> IDE 961"},
    {"codigo": "993509", "entidad": "EPS037", "type": "exact", "expected": "961", "note": "Vacuna Varicela + EPS037 -> IDE 961"},
    # --- EPSI05 (COMENTADO) ---
    # {"codigo": "906340", "entidad": "EPSI05", "type": "exact", "expected": "986", "note": "906340 + EPSI05 -> IDE 986"},
    # {"codigo": "906127", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Toxoplasma IGG + EPSI05 -> IDE 977"},
    # {"codigo": "906129", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Toxoplasma IGM + EPSI05 -> IDE 977"},
    # {"codigo": "906205", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "CMV IGG + EPSI05 -> IDE 977"},
    # {"codigo": "906206", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "CMV IGM + EPSI05 -> IDE 977"},
    # {"codigo": "906241", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Rubeola IGG + EPSI05 -> IDE 977"},
    # {"codigo": "906131", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Trypanosoma IGG + EPSI05 -> IDE 977"},
    # {"codigo": "990211", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Consejeria VIH + EPSI05 -> IDE 977"},
    # {"codigo": "897011", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Monitoria Fetal + EPSI05 -> IDE 977"},
    # {"codigo": "995201", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Otras Vac PAI SOD + EPSI05 -> IDE 977"},
    # {"codigo": "993513", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna VPH + EPSI05 -> IDE 977"},
    # {"codigo": "993520", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Doble Viral SR + EPSI05 -> IDE 977"},
    # {"codigo": "993106", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Neumococo + EPSI05 -> IDE 977"},
    # {"codigo": "993502", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Hepatitis A + EPSI05 -> IDE 977"},
    # {"codigo": "993503", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Hepatitis B + EPSI05 -> IDE 977"},
    # {"codigo": "993505", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Rabia + EPSI05 -> IDE 977"},
    # {"codigo": "993512", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Rotavirus + EPSI05 -> IDE 977"},
    # {"codigo": "993102", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "BCG + EPSI05 -> IDE 977"},
    # {"codigo": "993509", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Varicela + EPSI05 -> IDE 977"},
    # --- EPSIC5 (COMENTADO) ---
    # {"codigo": "906340", "entidad": "EPSIC5", "type": "exact", "expected": "980", "note": "906340 + EPSIC5 -> IDE 980"},
    # {"codigo": "906127", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Toxoplasma IGG + EPSIC5 -> IDE 979"},
    # {"codigo": "906129", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Toxoplasma IGM + EPSIC5 -> IDE 979"},
    # {"codigo": "906205", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "CMV IGG + EPSIC5 -> IDE 979"},
    # {"codigo": "906206", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "CMV IGM + EPSIC5 -> IDE 979"},
    # {"codigo": "906241", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Rubeola IGG + EPSIC5 -> IDE 979"},
    # {"codigo": "906131", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Trypanosoma IGG + EPSIC5 -> IDE 979"},
    # {"codigo": "990211", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Consejeria VIH + EPSIC5 -> IDE 979"},
    # {"codigo": "897011", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Monitoria Fetal + EPSIC5 -> IDE 979"},
    # {"codigo": "995201", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Otras Vac PAI SOD + EPSIC5 -> IDE 979"},
    # {"codigo": "993513", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Vacuna VPH + EPSIC5 -> IDE 979"},
    # {"codigo": "993520", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Doble Viral SR + EPSIC5 -> IDE 979"},
    # {"codigo": "993106", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Vacuna Neumococo + EPSIC5 -> IDE 979"},
    # {"codigo": "993502", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Vacuna Hepatitis A + EPSIC5 -> IDE 979"},
    # {"codigo": "993503", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Vacuna Hepatitis B + EPSIC5 -> IDE 979"},
    # {"codigo": "993505", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Vacuna Rabia + EPSIC5 -> IDE 979"},
    # {"codigo": "993512", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Vacuna Rotavirus + EPSIC5 -> IDE 979"},
    # {"codigo": "993102", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "BCG + EPSIC5 -> IDE 979"},
    # {"codigo": "993509", "entidad": "EPSIC5", "type": "exact", "expected": "979", "note": "Vacuna Varicela + EPSIC5 -> IDE 979"},
    # EPSI05 + EXAMENES PYM EVENTO -> IDE 977
    {"codigo": "906127", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Toxoplasma IGG + EPSI05 -> IDE 977"},
    {"codigo": "906129", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Toxoplasma IGM + EPSI05 -> IDE 977"},
    {"codigo": "906205", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "CMV IGG + EPSI05 -> IDE 977"},
    {"codigo": "906206", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "CMV IGM + EPSI05 -> IDE 977"},
    {"codigo": "906241", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Rubeola IGG + EPSI05 -> IDE 977"},
    {"codigo": "906131", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Trypanosoma IGG + EPSI05 -> IDE 977"},
    # EPSI05 + CODIGOS_PYM_INTRAMURAL -> IDE 977
    {"codigo": "990211", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Consejeria VIH + EPSI05 -> IDE 977"},
    {"codigo": "897011", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Monitoria Fetal + EPSI05 -> IDE 977"},
    {"codigo": "995201", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Otras Vac PAI SOD + EPSI05 -> IDE 977"},
    {"codigo": "993513", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna VPH + EPSI05 -> IDE 977"},
    {"codigo": "993520", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Doble Viral SR + EPSI05 -> IDE 977"},
    {"codigo": "993106", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Neumococo + EPSI05 -> IDE 977"},
    {"codigo": "993502", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Hepatitis A + EPSI05 -> IDE 977"},
    {"codigo": "993503", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Hepatitis B + EPSI05 -> IDE 977"},
    {"codigo": "993505", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Rabia + EPSI05 -> IDE 977"},
    {"codigo": "993512", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Rotavirus + EPSI05 -> IDE 977"},
    {"codigo": "993102", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "BCG + EPSI05 -> IDE 977"},
    {"codigo": "993509", "entidad": "EPSI05", "type": "exact", "expected": "977", "note": "Vacuna Varicela + EPSI05 -> IDE 977"},
    # --- ESSC18 (COMENTADO) ---
    # {"codigo": "906340", "entidad": "ESSC18", "type": "exact", "expected": "842", "note": "906340 + ESSC18 -> IDE 842"},
    # {"codigo": "993504", "entidad": "ESSC18", "type": "exact", "expected": "982", "note": "993504 + ESSC18 -> IDE 982"},
    # {"codigo": "906127", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Toxoplasma IGG + ESSC18 -> IDE 975"},
    # {"codigo": "906129", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Toxoplasma IGM + ESSC18 -> IDE 975"},
    # {"codigo": "906205", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "CMV IGG + ESSC18 -> IDE 975"},
    # {"codigo": "906206", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "CMV IGM + ESSC18 -> IDE 975"},
    # {"codigo": "906241", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Rubeola IGG + ESSC18 -> IDE 975"},
    # {"codigo": "906131", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Trypanosoma IGG + ESSC18 -> IDE 975"},
    # {"codigo": "990211", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Consejeria VIH + ESSC18 -> IDE 975"},
    # {"codigo": "897011", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Monitoria Fetal + ESSC18 -> IDE 975"},
    # {"codigo": "995201", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Otras Vac PAI SOD + ESSC18 -> IDE 975"},
    # {"codigo": "993513", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Vacuna VPH + ESSC18 -> IDE 975"},
    # {"codigo": "993520", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Doble Viral SR + ESSC18 -> IDE 975"},
    # {"codigo": "993106", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Vacuna Neumococo + ESSC18 -> IDE 975"},
    # {"codigo": "993502", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Vacuna Hepatitis A + ESSC18 -> IDE 975"},
    # {"codigo": "993503", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Vacuna Hepatitis B + ESSC18 -> IDE 975"},
    # {"codigo": "993505", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Vacuna Rabia + ESSC18 -> IDE 975"},
    # {"codigo": "993512", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Vacuna Rotavirus + ESSC18 -> IDE 975"},
    # {"codigo": "993102", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "BCG + ESSC18 -> IDE 975"},
    # {"codigo": "993509", "entidad": "ESSC18", "type": "exact", "expected": "975", "note": "Vacuna Varicela + ESSC18 -> IDE 975"},
    # --- ESS118 (COMENTADO) ---
    # {"codigo": "906340", "entidad": "ESS118", "type": "exact", "expected": "839", "note": "906340 + ESS118 -> IDE 839"},
    # {"codigo": "993504", "entidad": "ESS118", "type": "exact", "expected": "981", "note": "993504 + ESS118 -> IDE 981"},
    # --- ESS118 + EXAMENES PYM EVENTO -> IDE 974 (COMENTADO) ---
    # {"codigo": "906127", "entidad": "ESS118", "type": "exact", "expected": "974", "note": "Toxoplasma IGG"},
    # {"codigo": "906129", "entidad": "ESS118", "type": "exact", "expected": "974", "note": "Toxoplasma IGM"},
    # {"codigo": "906205", "entidad": "ESS118", "type": "exact", "expected": "974", "note": "CMV IGG"},
    # {"codigo": "906206", "entidad": "ESS118", "type": "exact", "expected": "974", "note": "CMV IGM"},
    # {"codigo": "906241", "entidad": "ESS118", "type": "exact", "expected": "974", "note": "Rubeola IGG"},
    # {"codigo": "906131", "entidad": "ESS118", "type": "exact", "expected": "974", "note": "Trypanosoma IGG"},
    # --- ESS118 + CODIGOS_PYM_INTRAMURAL -> IDE 970 (COMENTADO) ---
    # {"codigo": "990211", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Consejeria VIH"},
    # {"codigo": "897011", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Monitoria Fetal"},
    # {"codigo": "995201", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Otras Vac PAI SOD"},
    # {"codigo": "993513", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Vacuna VPH"},
    # {"codigo": "993520", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Doble Viral SR"},
    # {"codigo": "993106", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Vacuna Neumococo"},
    # {"codigo": "993502", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Vacuna Hepatitis A"},
    # {"codigo": "993503", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Vacuna Hepatitis B"},
    # {"codigo": "993505", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Vacuna Rabia"},
    # {"codigo": "993512", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Vacuna Rotavirus"},
    # {"codigo": "993102", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "BCG"},
    # {"codigo": "993509", "entidad": "ESS118", "type": "exact", "expected": "970", "note": "Vacuna Varicela"},
]

# =============================================================================
# Reglas de INSERCIÓN
# =============================================================================
IDE_INSERTION_RULES: list[dict[str, Any]] = []

# =============================================================================
# Reglas ESSC62 con 890405
# =============================================================================
IDE_ESSC62_890405_RULES: list[dict[str, Any]] = []

# =============================================================================
# Reglas MÚLTIPLES
# =============================================================================
IDE_MULTIPLE_RULES: list[dict[str, Any]] = []
