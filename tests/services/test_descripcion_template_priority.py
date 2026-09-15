"""TDD: descripcion_template tiene prioridad sobre formatters con nombre.

Caso testigo regla #60 sala_obs_soat, grupo Cups-Equivalentes:
template "Revisar códigos faltantes SOAT 39145 o 39131." debe mostrarse
en row["descripcion"], no la descripcion del formatter.
"""

from __future__ import annotations

SOAT_TEMPLATE = "Revisar códigos faltantes SOAT 39145 o 39131."


def test_cups_equivalentes_muestra_template_regla_60():
    from app.services.normalized_rows import build_normalized_rows

    rows = build_normalized_rows(
        error_groups={
            "Cups-Equivalentes": [
                {
                    "factura": "F60",
                    "codigo": ["38114"],
                    "procedimiento": "",
                    "estancia_str": "",
                    "problema": "descripcion generica del formatter",
                    "regla": "#60",
                }
            ]
        },
        responsables_map={},
        use_grupo_mapping=True,
        grupo_mappings={
            "Cups-Equivalentes": {
                "detalle_a_campo": None,
                "detalle_b_campo": None,
                "descripcion_template": SOAT_TEMPLATE,
            }
        },
    )
    assert rows[0]["descripcion"] == SOAT_TEMPLATE


def test_formatter_sin_template_mantiene_comportamiento():
    from app.services.normalized_rows import build_normalized_rows

    rows = build_normalized_rows(
        error_groups={
            "Cups-Equivalentes": [
                {
                    "factura": "F5",
                    "codigo": ["a1", "a2"],
                    "procedimiento": "",
                    "estancia_str": "2 días 3 horas",
                    "problema": "equiv",
                }
            ]
        },
        responsables_map={},
        use_grupo_mapping=True,
        grupo_mappings={},
    )
    assert rows[0]["descripcion"] == "equiv"
    assert rows[0]["procedimiento"] == "a1, a2"
    assert rows[0]["detalle"] == "Estancia: 2 días 3 horas"


def test_template_con_placeholder_resuelve():
    from app.services.normalized_rows import build_normalized_rows

    rows = build_normalized_rows(
        error_groups={
            "Cups-Equivalentes": [
                {
                    "factura": "F61",
                    "codigo": "39145",
                    "procedimiento": "",
                    "estancia_str": "",
                    "problema": "otro texto",
                    "codigo_faltante": "39131",
                }
            ]
        },
        responsables_map={},
        use_grupo_mapping=True,
        grupo_mappings={
            "Cups-Equivalentes": {
                "detalle_a_campo": None,
                "detalle_b_campo": None,
                "descripcion_template": "Falta código {codigo_faltante} en {factura}.",
            }
        },
    )
    assert rows[0]["descripcion"] == "Falta código 39131 en F61."


def test_item_template_viaja_en_item_sin_grupo_mapping():
    """El template puede viajar en el item (engine enriquecido)."""
    from app.services.normalized_rows import build_normalized_rows

    rows = build_normalized_rows(
        error_groups={
            "Cups-Equivalentes": [
                {
                    "factura": "F62",
                    "codigo": "38114",
                    "problema": "texto formatter",
                    "descripcion_template": SOAT_TEMPLATE,
                }
            ]
        },
        responsables_map={},
        use_grupo_mapping=True,
        grupo_mappings={},
    )
    assert rows[0]["descripcion"] == SOAT_TEMPLATE
