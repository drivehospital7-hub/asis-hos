"""TDD suite for dominio-grupo-error T11: parity / cutover / admin round-trip.

- Golden flag-off-vs-on diff harness (plain groups byte-equal; remapped
  groups differ only in the intended tipo_error label).
- Dangling-ref guard: every detalle_a/b field referenced by seeds resolves
  against the known finding-item key vocabulary.
- Admin round-trip: editing grupo_error regroups /procesar output.
"""

from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"

# Finding-item key vocabulary (legacy blocks' item.get keys + engine problem keys).
KNOWN_ITEM_KEYS = frozenset({
    "factura", "problema", "regla", "severidad", "param_config_id",
    "codigo", "codigo_equiv", "procedimiento", "tipo_identificacion",
    "codigo_entidad_cobrar", "tipo_procedimiento", "vlr_subsidiado",
    "vlr_procedimiento", "cantidad", "cantidad_esperada",
    "convenio_facturado", "centro_costo", "centro_actual", "centro_deberia",
    "ide_contrato", "ide_contrato_actual", "ide_contrato_deberia",
    "entidad_cobrar", "entidad_cobrar_nombre", "entidad_afiliacion", "entidad",
    "tipo_usuario", "tipo_actual", "tipo_deberia", "vlr_copago",
    "codigo_tipo_procedimiento", "laboratorio", "tarifario",
    "tipo_factura_descripcion", "responsable_cierra", "profesional_atiende",
    "identificacion", "numero_identificacion", "codigo_profesional",
    "fec_nacimiento", "fec_factura", "edad", "edad_anios", "edad_meses",
    "date.edad", "date.edad_meses", "numero_identificacion",
    "cod_entidad_actual", "cod_entidad_esperado",
    "codigo_tipo_procedimiento", "total_pares", "pares_duplicados",
    "estancia_str", "accion", "observacion", "detalle", "descripcion",
    "tipo_factura", "prioridad", "nota", "facturas", "cantidad_repeticiones",
    "invoice",
})


def _seed_mapping_refs() -> list[tuple[str, str, str]]:
    """Collect (seed, rule, field-ref) triples from seed grouping columns."""
    refs: list[tuple[str, str, str]] = []
    pattern = re.compile(
        r"INSERT INTO reglas\s*\((?P<cols>[^)]+)\)\s*"
        r"VALUES\s*\((?P<vals>.*?)\)\s*"
        r"ON CONFLICT\s*\(nombre,\s*version\)",
        re.IGNORECASE | re.DOTALL,
    )
    for seed in sorted(MIGRATIONS_DIR.glob("01[0-6]_*.sql")):
        for match in pattern.finditer(seed.read_text(encoding="utf-8")):
            cols = [c.strip() for c in match.group("cols").split(",")]
            if "detalle_a_campo" not in cols:
                continue
            name_m = re.match(r"\s*'([^']+)'", match.group("vals"))
            rule = name_m.group(1) if name_m else "?"
            strvals = re.findall(
                r"'((?:[^']|'{2})*)'|(\b\d+\b|true|false|NULL)", match.group("vals")
            )
            flat = [
                a.replace("''", "'") if b == "" else None for a, b in strvals
            ]
            for col in ("detalle_a_campo", "detalle_b_campo", "descripcion_template"):
                value = flat[cols.index(col)]
                if value:
                    refs.append((seed.name, rule, value))
    return refs


def _field_atoms(ref: str) -> list[str]:
    """Extract bare field names: {placeholders}, comma field lists, or one field."""
    if ref.startswith("="):
        return []
    if "{" in ref:
        return re.findall(r"\{([^{}]+)\}", ref)
    if "," in ref:
        return [p.strip() for p in ref.split(",") if p.strip()]
    if " " in ref.strip():
        return []  # prose literal (e.g. Decimales template), not a field ref
    return [ref.strip()] if ref.strip() else []


class TestDanglingMappingRefs:
    def test_every_mapped_field_resolves_to_known_key(self):
        refs = _seed_mapping_refs()
        assert len(refs) > 40, "expected dozens of seed mapping refs"
        dangling = [
            (seed, rule, atom)
            for seed, rule, ref in refs
            for atom in _field_atoms(ref)
            if atom not in KNOWN_ITEM_KEYS
        ]
        assert not dangling, f"dangling mapping refs: {dangling[:5]}"


class TestGoldenFlagDiff:
    def _legacy_groups(self):
        return {
            "Centros de Costo": [
                {
                    "factura": "F1", "codigo": "c1", "procedimiento": "p1",
                    "problema": "cc bad", "centro_actual": "U",
                    "centro_costo": "U", "regla": "#1",
                }
            ],
            "Decimales": [{"factura": "F2", "regla": "#2"}],
            "Duplicados Farmacia": [
                {
                    "factura": "F3", "codigo_tipo_procedimiento": "01",
                    "total_pares": 1, "pares_duplicados": [],
                    "problema": "", "regla": "#3",
                }
            ],
        }

    def _mapped_groups(self):
        return {
            "Centros de Costo": [
                {
                    "factura": "F1", "codigo": "c1", "procedimiento": "p1",
                    "problema": "cc bad", "centro_actual": "U",
                    "centro_costo": "U", "regla": "#1",
                }
            ],
            "Decimales": [{"factura": "F2", "regla": "#2"}],
            "Duplicados-Farmacia": [
                {
                    "factura": "F3", "codigo_tipo_procedimiento": "01",
                    "total_pares": 1, "pares_duplicados": [],
                    "problema": "", "regla": "#3",
                }
            ],
        }

    def _mappings(self):
        return {
            "Centros de Costo": {
                "detalle_a_campo": "codigo,procedimiento",
                "detalle_b_campo": "centro_actual,centro_costo",
                "descripcion_template": None,
            },
            "Decimales": {
                "detalle_a_campo": "=Vlr. Procedimiento",
                "detalle_b_campo": "=Vlr. Subsidiado",
                "descripcion_template": "Valores con decimales",
            },
        }

    def test_plain_groups_byte_equal_flag_on(self):
        from app.services.normalized_rows import build_normalized_rows

        legacy = build_normalized_rows(
            error_groups=self._legacy_groups(), responsables_map={}
        )
        mapped = build_normalized_rows(
            error_groups=self._mapped_groups(),
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings=self._mappings(),
        )
        by_factura_legacy = {r["factura"]: r for r in legacy}
        by_factura_mapped = {r["factura"]: r for r in mapped}
        for factura in ("F1", "F2"):
            assert "mapping_completa" not in by_factura_mapped[factura]
            assert {
                k: v for k, v in by_factura_mapped[factura].items()
                if k != "regla"
            } == {
                k: v for k, v in by_factura_legacy[factura].items() if k != "regla"
            }

    def test_remapped_group_diff_is_intended_only(self):
        from app.services.normalized_rows import build_normalized_rows

        legacy = build_normalized_rows(
            error_groups=self._legacy_groups(), responsables_map={}
        )
        mapped = build_normalized_rows(
            error_groups=self._mapped_groups(),
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings=self._mappings(),
        )
        legacy_f3 = next(r for r in legacy if r["factura"] == "F3")
        mapped_f3 = next(r for r in mapped if r["factura"] == "F3")
        assert legacy_f3["tipo_error"] == "⚠️ Revisión Necesaria"
        assert mapped_f3["tipo_error"] == "Revision-Necesaria"
        assert mapped_f3["detalle"] == legacy_f3["detalle"]


class TestAdminRoundTrip:
    def _db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.database import Base
        import app.models  # noqa: F401

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)()

    def test_editing_grupo_error_regroups_procesar_output(self):
        from app.services.reglas import rule_service
        from app.services.normalized_rows import build_normalized_rows

        db = self._db()
        created = rule_service.create_rule(
            db, {"nombre": "roundtrip_rule", "dominio": "urgencias"}
        )
        rule_service.update_rule(
            db,
            created["id"],
            {
                "grupo_error": "Centros de Costo",
                "detalle_a_campo": "codigo,procedimiento",
                "detalle_b_campo": "centro_actual,centro_costo",
                "descripcion_template": None,
            },
        )
        stored = rule_service.get_rule(db, created["id"])
        mappings = {
            stored["grupo_error"]: {
                "detalle_a_campo": stored["detalle_a_campo"],
                "detalle_b_campo": stored["detalle_b_campo"],
                "descripcion_template": stored["descripcion_template"],
            }
        }
        rows = build_normalized_rows(
            error_groups={
                stored["grupo_error"]: [
                    {
                        "factura": "F9", "codigo": "c9", "procedimiento": "p9",
                        "problema": "bad", "centro_actual": "U",
                        "regla": f"#{created['id']}",
                    }
                ]
            },
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings=mappings,
        )
        assert rows[0]["tipo_error"] == "Centros de Costo"
        assert rows[0]["procedimiento"] == "c9 - p9"
        assert rows[0]["detalle"] == "U"
        assert rows[0]["regla"] == f"#{created['id']}"
