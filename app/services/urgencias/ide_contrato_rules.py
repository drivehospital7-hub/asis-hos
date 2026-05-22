"""Mapping de reglas IDE Contrato para Urgencias.

TIPO: Data/config, NO código procedural.
Cada regla es un dict con:
- codigo: Código CUPS a validar
- entidad: Cód Entidad Cobrar a validar
- type: tipo de regla ("exact", "insertion", "has_890405", "multiple", "generic")
- expected: valor(es) esperado(s) de IDE Contrato

Reglas por tipo:
  * exact: (codigo+entidad) → un único IDE esperado
  * insertion: (codigo+entidad) → IDE distinto si la identificación tiene código 861801
  * has_890405: (codigo+entidad) → IDE distinto si la identificación tiene código 890405 (solo ESSC62)
  * multiple: (codigo+entidad) → conjunto de IDEs válidos (cualquiera sirve)
  * generic: (entidad) → un único IDE esperado, independiente del código
  * generic_multiple: (entidad) → conjunto de IDEs válidos
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# Reglas EXACTAS: (codigo, entidad) → IDE único esperado
# =============================================================================
IDE_SIMPLE_RULES: list[dict[str, Any]] = [
    # Regla 6: Código=906340 + Entidad=EPSI05 -> IDE 986
    {
        "codigo": "906340",
        "entidad": "EPSI05",
        "type": "exact",
        "expected": "986",
        "note": "906340 + EPSI05 -> IDE 986",
    },
    # Regla 7: Código=861801 + Entidad=EPSI05 -> IDE 977
    {
        "codigo": "861801",
        "entidad": "EPSI05",
        "type": "exact",
        "expected": "977",
        "note": "861801 + EPSI05 -> IDE 977",
    },
    # Regla 9: Código=861801 + Entidad=EPSIC5 -> IDE 979
    {
        "codigo": "861801",
        "entidad": "EPSIC5",
        "type": "exact",
        "expected": "979",
        "note": "861801 + EPSIC5 -> IDE 979",
    },
    # Regla 13: Código=906340 + Entidad=ESS118 -> IDE 839
    {
        "codigo": "906340",
        "entidad": "ESS118",
        "type": "exact",
        "expected": "839",
        "note": "906340 + ESS118 -> IDE 839",
    },
    # Regla 18: Código=906340 + Entidad=ESSC18 -> IDE 842
    {
        "codigo": "906340",
        "entidad": "ESSC18",
        "type": "exact",
        "expected": "842",
        "note": "906340 + ESSC18 -> IDE 842",
    },
    # Regla 17: Código=861801 + Entidad=ESSC18 -> IDE 975
    {
        "codigo": "861801",
        "entidad": "ESSC18",
        "type": "exact",
        "expected": "975",
        "note": "861801 + ESSC18 -> IDE 975",
    },
    # Regla 25: Código=861801 + Entidad=ESS062 -> IDE 922
    {
        "codigo": "861801",
        "entidad": "ESS062",
        "type": "exact",
        "expected": "922",
        "note": "861801 + ESS062 -> IDE 922",
    },
    # Regla 27: Código=861801 + Entidad=ESSC62 -> IDE 863
    {
        "codigo": "861801",
        "entidad": "ESSC62",
        "type": "exact",
        "expected": "863",
        "note": "861801 + ESSC62 -> IDE 863",
    },
    # Regla 19: Código=906340 + Entidad=EPS037 -> IDE 962
    {
        "codigo": "906340",
        "entidad": "EPS037",
        "type": "exact",
        "expected": "962",
        "note": "906340 + EPS037 -> IDE 962",
    },
    # Regla 20: Código=861801 + Entidad=EPS037 -> IDE 961
    {
        "codigo": "861801",
        "entidad": "EPS037",
        "type": "exact",
        "expected": "961",
        "note": "861801 + EPS037 -> IDE 961",
    },
    # Regla 22: Código=906340 + Entidad=EPSS41 -> IDE 959
    {
        "codigo": "906340",
        "entidad": "EPSS41",
        "type": "exact",
        "expected": "959",
        "note": "906340 + EPSS41 -> IDE 959",
    },
    # Regla 23: Código=861801 + Entidad=EPSS41 -> IDE 958
    {
        "codigo": "861801",
        "entidad": "EPSS41",
        "type": "exact",
        "expected": "958",
        "note": "861801 + EPSS41 -> IDE 958",
    },
    # Regla 31: Código=861801 + Entidad=86000 -> IDE 920
    {
        "codigo": "861801",
        "entidad": "86000",
        "type": "exact",
        "expected": "920",
        "note": "861801 + 86000 -> IDE 920",
    },
    # Regla 32: Código=861801 + Entidad=RES004 -> IDE 908
    {
        "codigo": "861801",
        "entidad": "RES004",
        "type": "exact",
        "expected": "908",
        "note": "861801 + RES004 -> IDE 908",
    },
    # ESS118 + Código=890405 -> IDE 974
    {
        "codigo": "890405",
        "entidad": "ESS118",
        "type": "exact",
        "expected": "974",
        "note": "890405 + ESS118 -> IDE 974",
    },
    # ESS118 + Código=890205 -> IDE 970
    {
        "codigo": "890205",
        "entidad": "ESS118",
        "type": "exact",
        "expected": "970",
        "note": "890205 + ESS118 -> IDE 970",
    },
]

# =============================================================================
# Reglas CONDICIONALES por inserción 861801
# (codigo, entidad) → (IDE_con_insercion, IDE_sin_insercion)
# =============================================================================
IDE_INSERTION_RULES: list[dict[str, Any]] = [
    # Regla 8: Código=890405 + Entidad=EPSI05
    # Si identificación tiene 861801 -> IDE 976, si no -> IDE 977
    {
        "codigo": "890405",
        "entidad": "EPSI05",
        "type": "insertion",
        "expected_with": "976",
        "expected_without": "977",
        "note": "890405 + EPSI05 -> IDE 976 (con 861801) / 977 (sin 861801)",
    },
    # Regla 10: Código=890405 + Entidad=EPSIC5
    {
        "codigo": "890405",
        "entidad": "EPSIC5",
        "type": "insertion",
        "expected_with": "967",
        "expected_without": "979",
        "note": "890405 + EPSIC5 -> IDE 967 (con 861801) / 979 (sin 861801)",
    },
    # Regla 18: Código=890405 + Entidad=ESSC18
    {
        "codigo": "890405",
        "entidad": "ESSC18",
        "type": "insertion",
        "expected_with": "968",
        "expected_without": "975",
        "note": "890405 + ESSC18 -> IDE 968 (con 861801) / 975 (sin 861801)",
    },
    # Regla 21: Código=890405 + Entidad=EPS037
    {
        "codigo": "890405",
        "entidad": "EPS037",
        "type": "insertion",
        "expected_with": "962",
        "expected_without": "961",
        "note": "890405 + EPS037 -> IDE 962 (con 861801) / 961 (sin 861801)",
    },
    # Regla 24: Código=890405 + Entidad=EPSS41
    {
        "codigo": "890405",
        "entidad": "EPSS41",
        "type": "insertion",
        "expected_with": "959",
        "expected_without": "958",
        "note": "890405 + EPSS41 -> IDE 959 (con 861801) / 958 (sin 861801)",
    },
    # Regla 26: Código=890405 + Entidad=ESS062
    {
        "codigo": "890405",
        "entidad": "ESS062",
        "type": "insertion",
        "expected_with": "921",
        "expected_without": "922",
        "note": "890405 + ESS062 -> IDE 921 (con 861801) / 922 (sin 861801)",
    },
    # Regla 34: Código=890405 + Entidad=86000
    {
        "codigo": "890405",
        "entidad": "86000",
        "type": "insertion",
        "expected_with": "919",
        "expected_without": "920",
        "note": "890405 + 86000 -> IDE 919 (con 861801) / 920 (sin 861801)",
    },
    # Regla 33: Código=890405 + Entidad=RES004
    {
        "codigo": "890405",
        "entidad": "RES004",
        "type": "insertion",
        "expected_with": "908",
        "expected_without": "909",
        "note": "890405 + RES004 -> IDE 908 (con 861801) / 909 (sin 861801)",
    },
]

# =============================================================================
# Reglas CONDICIONALES por presencia de 890405 (solo ESSC62)
# (codigo, entidad) → (IDE_con_890405, IDE_sin_890405)
# =============================================================================
IDE_ESSC62_890405_RULES: list[dict[str, Any]] = [
    # Regla 28: ESSC62 + Código=890405
    # Si identificación tiene 890405 en otro procedimiento -> IDE 862
    # Si identificación NO tiene 890405 -> IDE 863
    {
        "codigo": "890405",
        "entidad": "ESSC62",
        "type": "has_890405",
        "expected_with": "862",
        "expected_without": "863",
        "note": "890405 + ESSC62 -> IDE 862 (con 890405) / 863 (sin 890405)",
    },
]

# =============================================================================
# Reglas MÚLTIPLES: (codigo, entidad) → conjunto de IDEs válidos
# =============================================================================
IDE_MULTIPLE_RULES: list[dict[str, Any]] = [
    # Regla 12: ESS118 + Código=735301 -> IDE 970 o 974
    {
        "codigo": "735301",
        "entidad": "ESS118",
        "type": "multiple",
        "expected_set": frozenset({"970", "974"}),
        "note": "735301 + ESS118 -> IDE 970 o 974",
    },
    # ESS118 + Código=861801 -> IDE 970 o 974
    {
        "codigo": "861801",
        "entidad": "ESS118",
        "type": "multiple",
        "expected_set": frozenset({"970", "974"}),
        "note": "861801 + ESS118 -> IDE 970 o 974",
    },
]
