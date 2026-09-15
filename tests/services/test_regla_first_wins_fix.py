"""TDD: first-wins no debe pisar row[regla].

Caso testigo: CAP545490, grupo Cups-Equivalentes, items #9 y #51
misma factura -> cada row conserva su propia regla (1:1).
"""

from __future__ import annotations


def test_misma_factura_conserva_regla_propia_9_y_51():
    from app.services.normalized_rows import build_normalized_rows

    rows = build_normalized_rows(
        error_groups={
            "Cups-Equivalentes": [
                {
                    "factura": "CAP545490",
                    "codigo": "890701",
                    "procedimiento": "p9",
                    "problema": "problema 9",
                    "regla": "#9",
                },
                {
                    "factura": "CAP545490",
                    "codigo": "890601",
                    "procedimiento": "p51",
                    "problema": 'Verifica que si hay codigos 890701 o 890601',
                    "regla": "#51",
                },
            ]
        },
        responsables_map={},
        use_grupo_mapping=True,
        grupo_mappings={},
    )
    assert len(rows) == 2
    reglas = sorted(r.get("regla") for r in rows)
    assert reglas == ["#51", "#9"], f"first-wins piso regla: {reglas}"
    by_proc = {r["procedimiento"]: r.get("regla") for r in rows}
    assert by_proc["p9"] == "#9"
    assert by_proc["p51"] == "#51"


def test_attach_solo_fallback_cuando_row_sin_regla():
    from app.services.normalized_rows import _attach_regla_and_fallback

    rows = [
        {"factura": "F1", "tipo_error": "G", "regla": "#51",
         "procedimiento": "p", "detalle": "d"},
        {"factura": "F1", "tipo_error": "G",
         "procedimiento": "p", "detalle": "d"},
    ]
    groups = {
        "G": [
            {"factura": "F1", "regla": "#9"},
            {"factura": "F1", "regla": "#51"},
        ]
    }
    _attach_regla_and_fallback(rows, groups, {})
    assert rows[0]["regla"] == "#51", "no debe pisar regla ya presente"
    assert rows[1]["regla"] == "#9", "fallback first-wins solo si falta"
