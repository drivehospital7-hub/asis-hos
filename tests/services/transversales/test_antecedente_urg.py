"""Unit tests for antecedente_urg (pure, no DB)."""

from app.services.transversales.antecedente_urg import compute_urg_hosp_24h_flags


def _row(doc, tipo, fec):
    return {
        "identificacion": doc,
        "tipo_factura_descripcion": tipo,
        "fec_factura": fec,
    }


def test_marca_intramural_con_urg_previa_24h():
    rows = [
        _row("D1", "Urgencias", "2026-10-05 10:00:00"),
        _row("D1", "Intramural", "2026-10-05 20:00:00"),
    ]
    assert compute_urg_hosp_24h_flags(rows) >= 1
    assert rows[1]["tuvo_urg_hosp_24h"] is True


def test_no_marca_fuera_de_ventana():
    rows = [
        _row("D1", "Hospitalización", "2026-10-01 10:00:00"),
        _row("D1", "Intramural", "2026-10-05 20:00:00"),
    ]
    assert compute_urg_hosp_24h_flags(rows) == 0
    assert rows[1]["tuvo_urg_hosp_24h"] is False


def test_no_marca_otro_paciente_ni_futuro():
    rows = [
        _row("D1", "Urgencias", "2026-10-05 10:00:00"),
        _row("D2", "Intramural", "2026-10-05 20:00:00"),
        _row("D1", "Intramural", "2026-10-04 20:00:00"),  # urg es posterior
    ]
    compute_urg_hosp_24h_flags(rows)
    assert rows[1]["tuvo_urg_hosp_24h"] is False
    assert rows[2]["tuvo_urg_hosp_24h"] is False


def test_fechas_invalidas_no_rompen():
    rows = [
        _row("D1", "Urgencias", None),
        _row("D1", "Intramural", "no-fecha"),
        {"identificacion": None},
    ]
    assert compute_urg_hosp_24h_flags(rows) == 0
    assert all(r.get("tuvo_urg_hosp_24h") is False for r in rows)
