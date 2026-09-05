# Design — PROFESIONALES_EXCEPTUADOS_CRONOGRAMA

> **Change**: Agregar excepción para MADROÑERO BURBANO KAREN LIZETH (02217) en el detector de bacteriólogas vs cronograma, permitiendo que facture cualquier día sin validación de horario.

---

## 1. Component Diagram

### Before (current flow)

```
Excel Row
  │
  ├─ Filtros tempranos: Intramural, Tipo 02/05, Laboratorio=Si
  │
  ├─ ¿Código CUPS en EXCEPCIONES_BACTERIOLOGA? ──Si──→ continue
  │
  ├─ Lookup PROFESIONALES_URGENCIAS[codigo_prof]
  │   └─ ¿No existe? ──→ ERROR: "no está en listado Urgencias"
  │   └─ ¿tipo ≠ BACTERIOLOGA? ──→ ERROR: "no es una bacterióloga"
  │
  ├─ ¿responsable_cierra en FACTURADORES_URGENCIAS? ──Si──→ continue
  │
  ├─ siglas_filter según responsable_cierra (Chapuel→PYM, Tapia/Ordoñez→CE, default→None)
  │
  ├─ get_turno_del_dia(fecha, siglas_filter)
  │   └─ ¿No hay turnos? ──→ continue (sin error)
  │
  └─ ¿codigo_prof in codigos_en_turno? ──No──→ ERROR: "no está en cronograma"
```

### After (new flow)

```
Excel Row
  │
  ├─ Filtros tempranos: Intramural, Tipo 02/05, Laboratorio=Si
  │
  ├─ ¿Código CUPS en EXCEPCIONES_BACTERIOLOGA? ──Si──→ continue
  │
  ├─ Lookup PROFESIONALES_URGENCIAS[codigo_prof]
  │   └─ ¿No existe? ──→ ERROR: "no está en listado Urgencias"
  │   └─ ¿tipo ≠ BACTERIOLOGA? ──→ ERROR: "no es una bacterióloga"
  │
  ├─ ★ NEW: ¿codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA? ──Si──→ continue
  │   (Bypass total de cronograma — MADROÑERO factura cualquier día)
  │
  ├─ ¿responsable_cierra en FACTURADORES_URGENCIAS? ──Si──→ continue
  │
  ├─ siglas_filter según responsable_cierra
  ├─ get_turno_del_dia(...)
  └─ ¿codigo_prof in codigos_en_turno? ──No──→ ERROR
```

**Key insight**: The new check sits AFTER confirming the professional exists AND is a BACTERIOLOGA (we still want those validations), but BEFORE any `responsable_cierra`, `siglas_filter`, or cronograma resolution. It's the earliest possible exit after the BACTERIOLOGA type gate.

---

## 2. Data Model

### New constant — `app/constants/urgencias.py`

Inserted **after line 47** (`EXCEPCIONES_BACTERIOLOGA`), preserving alphabetical/logical grouping:

```python
# Professionales que bypassan completamente la validación de cronograma de bacteriólogas
PROFESIONALES_EXCEPTUADOS_CRONOGRAMA: frozenset[str] = frozenset({"02217"})
```

**Why `frozenset`**:
- Immutable (same pattern as `EXCEPCIONES_BACTERIOLOGA`, `FACTURADORES_URGENCIAS`)
- O(1) membership lookup
- Signals this is a fixed, non-extensible set at runtime

**Why placed after `EXCEPCIONES_BACTERIOLOGA`**:
- `EXCEPCIONES_BACTERIOLOGA` (line 47) is about CUPS codes that bypass tipo/laboratorio filters — related concept to "exceptions"
- Placing it right after keeps exception-related constants together
- Before `CODIGOS_EXCEPTUADOS` (line 48) which are CUPS codes for a different domain

### Import — `app/services/intramural/bacteriologas_cronograma.py`

Add to the existing import from `app.constants.urgencias`:

```python
from app.constants.urgencias import (
    EXCEPCIONES_BACTERIOLOGA,
    FACTURADORES_URGENCIAS,
    PROFESIONALES_EXCEPTUADOS_CRONOGRAMA,  # ← NEW
    PROFESIONALES_URGENCIAS,
)
```

---

## 3. Execution Trace

### Scenario A: MADROÑERO (02217) — NOT in cronograma → NO error

| Step | Line(s) | Action | Result |
|------|---------|--------|--------|
| 1 | 174–178 | Read row, normalize factura | `factura = "FAC-001"` |
| 2 | 185–195 | `tipo_factura == "Intramural"` | ✅ Sigue |
| 3 | 198–208 | `tipo_proc in {"02", "05"}` | ✅ Sigue |
| 4 | 211–221 | `laboratorio == "Si"` | ✅ Sigue |
| 5 | 224–232 | `codigo_str in EXCEPCIONES_BACTERIOLOGA` | ❌ No está → Sigue |
| 6 | 235–241 | Read `codigo_prof = "02217"` | ✅ Sigue |
| 7 | 269 | `PROFESIONALES_URGENCIAS.get("02217")` | ✅ Encuentra: `{"nombre": "MADROÑERO BURBANO KAREN LIZETH", "tipo": "BACTERIOLOGA"}` |
| 8 | 291 | `tipo_profesional == "BACTERIOLOGA"` | ✅ Sí → Sigue |
| 9 | **NEW** | `"02217" in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` | ✅ **Sí → continue** 🚀 |
| — | 309+ | responsable_cierra, siglas_filter, get_turno_del_dia | **SKIPPED** |

### Scenario B: MOLINA ALVAREZ (03374) — NOT in cronograma → ERROR

| Step | Line(s) | Action | Result |
|------|---------|--------|--------|
| 1–6 | same | Filtros previos | ✅ Sigue |
| 7 | 269 | `PROFESIONALES_URGENCIAS.get("03374")` | ✅ Encuentra: BACTERIOLOGA |
| 8 | 291 | `tipo_profesional == "BACTERIOLOGA"` | ✅ Sí → Sigue |
| 9 | **NEW** | `"03374" in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` | ❌ **No está → Sigue** |
| 10 | 309+ | responsable_cierra, siglas_filter, get_turno_del_dia | Ejecuta normalmente |
| 11 | 352 | `codigo_prof not in codigos_en_turno` | ✅ No está → **ERROR** |

### Scenario C: MADROÑERO (02217) — IS in cronograma → NO error

Same as Scenario A, step 9 always fires `continue`. Even if she's scheduled, the bypass means no error (identical outcome by spec).

### Scenario D: PALACIOS (02249, MEDICO) — ERROR por no ser BACTERIOLOGA

| Step | Line(s) | Action | Result |
|------|---------|--------|--------|
| 1–6 | same | Filtros previos | ✅ Sigue |
| 7 | 269 | `PROFESIONALES_URGENCIAS.get("02249")` | ✅ Encuentra: MEDICO |
| 8 | 291 | `tipo_profesional == "BACTERIOLOGA"` | ❌ No → **ERROR: "no es una bacterióloga"** |
| — | **NEW** | Nunca se evalúa | El continue en 306 salta antes |

This confirms the check location is correct: MADROÑERO must still be a BACTERIOLOGA to get the exception.

---

## 4. Test Strategy

### 4.1 Unit tests — new class `TestProfesionalesExceptuados`

Add to `tests/services/test_intramural_bacteriologas_cronograma.py`:

```python
class TestProfesionalesExceptuados:
    """PROFESIONALES_EXCEPTUADOS_CRONOGRAMA bypass tests."""

    def test_madronero_sin_cronograma_no_error(self, monkeypatch):
        """02217 (MADROÑERO) NO está en cronograma → NO error."""
        monkeypatch.setattr(
            "app.services.intramural.bacteriologas_cronograma.get_turno_del_dia",
            lambda mes, anio, dia, siglas_filter=None: [
                {"nombre": "PABON GARCIA ALEJANDRA"}  # otra bacterióloga
            ],
        )
        wb, indices = _build_workbook([
            {
                "Numero Factura": "FAC-001",
                "Tipo Factura Descripcion": "Intramural",
                "Codigo Tipo Procedimiento": "02",
                "Laboratorio": "Si",
                "Codigo": "904902",
                "Codigo Profesional": "02217",
                "Profesional Atiende": "MADROÑERO BURBANO KAREN LIZETH",
                "Procedimiento": "Hormona Estimulante del Tiroides [TSH]",
                "Fec Factura": "15/03/2024",
            },
        ])
        result = detect_bacteriologas_cronograma(wb.active, indices)
        assert result == []

    def test_madronero_con_cronograma_no_error(self, monkeypatch):
        """02217 (MADROÑERO) SÍ está en cronograma → NO error."""
        monkeypatch.setattr(
            "app.services.intramural.bacteriologas_cronograma.get_turno_del_dia",
            lambda mes, anio, dia, siglas_filter=None: [
                {"nombre": "MADROÑERO BURBANO KAREN LIZETH"}
            ],
        )
        wb, indices = _build_workbook([
            {
                "Numero Factura": "FAC-001",
                ...
                "Codigo Profesional": "02217",
                ...
            },
        ])
        result = detect_bacteriologas_cronograma(wb.active, indices)
        assert result == []

    def test_otra_bacteriologa_sin_cronograma_si_error(self, monkeypatch):
        """03374 (MOLINA ALVAREZ) NO está en cronograma → ERROR."""
        monkeypatch.setattr(
            "app.services.intramural.bacteriologas_cronograma.get_turno_del_dia",
            lambda mes, anio, dia, siglas_filter=None: [],
        )
        wb, indices = _build_workbook([
            {
                "Numero Factura": "FAC-001",
                ...
                "Codigo Profesional": "03374",
                "Profesional Atiende": "MOLINA ALVAREZ KAROL DAYANNA",
                ...
            },
        ])
        result = detect_bacteriologas_cronograma(wb.active, indices)
        assert len(result) == 1
        assert "no está en el cronograma" in result[0]["problema"]

    def test_madronero_no_bacteriologa_no_bypass(self):
        """Si 02217 NO fuese BACTERIOLOGA (hipotético), no aplica excepción.
        Test existente de tipo no-BACTERIOLOGA ya cubre este caso."""
```

### 4.2 Mock strategy

Use `monkeypatch.setattr` on the same target used by existing tests:

```
"app.services.intramural.bacteriologas_cronograma.get_turno_del_dia"
```

No new mocking infrastructure needed.

### 4.3 Regression coverage

| Existing test | Impact |
|---|---|
| `test_bacteriologa_fuera_cronograma_error` | ✅ Still produces error for non-excepted prof |
| `test_bacteriologa_en_cronograma_no_error` | ✅ Unchanged |
| `test_facturadores_urgencias_bypass` | ✅ Unchanged (exception check fires first) |
| `test_profesional_no_bacteriologa_error` | ✅ Unchanged (exception never reached) |
| `test_profesional_no_en_listado_error` | ✅ Unchanged (exception never reached) |

No existing tests need modification.

---

## 5. Integration Points

### 5.1 Interaction with FACTURADORES_URGENCIAS bypass

The new check (line ~307) fires BEFORE the FACTURADORES_URGENCIAS check (line ~311). For MADROÑERO:

- If her `responsable_cierra` maps to a FACTURADORES_URGENCIAS member → the exception fires first, `continue` exits early. Both bypasses would produce the same result (no error), but the exception is more specific.
- No conflict: both paths end in `continue` with no side effects.

### 5.2 Interaction with siglas_filter per responsable

Since the exception fires before siglas_filter resolution, MADROÑERO's rows never reach:
- `resp` normalization (line 309)
- Chapuel/Tapia/Ordoñez branching (lines 315–320)
- `get_turno_del_dia()` call (lines 333–338)

This means the cronograma service is never called for her — which is the whole point.

### 5.3 Interaction with `detect_all.py`

Zero changes needed. The `detect_all` orchestrator calls `detect_bacteriologas_cronograma()` and receives its return list. If the list is empty for MADROÑERO, that's the correct result. No new parameters, no new wiring.

### 5.4 Interaction with `_build_nombre_a_codigo()` (reverse lookup)

The module-level `_NOMBRE_A_CODIGO` dict (line 58) is still built from all `PROFESIONALES_URGENCIAS`. MADROÑERO remains in the lookup — this is harmless since the exception check fires before cronograma resolution.

### 5.5 Interaction with `responsable_cierra=None` (default behavior)

When `responsable_cierra` is None, the function still works: the exception check fires at line ~307, and MADROÑERO is skipped before reaching the `resp = " ".join(...)` line.

---

## 6. Changelog

| File | Change |
|---|---|
| `app/constants/urgencias.py` | Add `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` constant (line 48) |
| `app/services/intramural/bacteriologas_cronograma.py` | Add import + check after line 306 |
| `tests/services/test_intramural_bacteriologas_cronograma.py` | Add `TestProfesionalesExceptuados` class |

3 files, ~25 lines of production code, ~60 lines of tests.
