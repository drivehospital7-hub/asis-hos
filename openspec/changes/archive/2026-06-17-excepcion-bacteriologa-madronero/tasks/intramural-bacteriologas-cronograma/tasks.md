# Tasks — PROFESIONALES_EXCEPTUADOS_CRONOGRAMA

> **Change**: Agregar excepción para MADROÑERO BURBANO KAREN LIZETH (02217) en el detector de bacteriólogas vs cronograma, permitiendo que facture cualquier día sin validación de horario.

---

## Workload Forecast

| Metric | Value |
|--------|-------|
| **Files changed** | 3 |
| **Production lines added** | ~5 |
| **Test lines added** | ~60 |
| **Total lines** | ~65 |
| **Risk level** | **LOW** |

✅ Well under 400 lines. No risk of threshold issues.

### Risk factors
- **Low**: No API/route changes, no schema changes, no new dependencies
- **Low**: Single-entry `frozenset`, deterministic logic, no branching complexity
- **Low**: All existing tests pass unchanged (per design regression analysis)
- **Notable**: Check placement is precise — must go AFTER BACTERIOLOGA type gate, BEFORE `responsable_cierra` / `siglas_filter` / `get_turno_del_dia`. Any movement breaks spec.

---

## Dependencies

```
T1 (constant) → T2 (import) → T3 (logic) → T4 (tests)
```

All tasks are strictly sequential. T1 must merge before T2 can compile, T2 before T3, T3 before T4 can pass.

---

## Tasks

### T1 — Add `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` constant

| Field | Value |
|-------|-------|
| **File** | `app/constants/urgencias.py` |
| **Action** | Insert new constant |
| **Insert after** | Line 47 (`EXCEPCIONES_BACTERIOLOGA`), before line 48 (`CODIGOS_EXCEPTUADOS`) |
| **Change description** | Add a new `frozenset[str]` constant named `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` containing code `"02217"`, with comment explaining it bypasses cronograma validation for bacteriólogas. |
| **Exact code** | ```python
# Profesionales que bypassan completamente la validación de cronograma de bacteriólogas
PROFESIONALES_EXCEPTUADOS_CRONOGRAMA: frozenset[str] = frozenset({"02217"})
``` |
| **Verification** | Run `python -c "from app.constants.urgencias import PROFESIONALES_EXCEPTUADOS_CRONOGRAMA; print(PROFESIONALES_EXCEPTUADOS_CRONOGRAMA)"` and confirm output is `frozenset({'02217'})` |

---

### T2 — Add import in `bacteriologas_cronograma.py`

| Field | Value |
|-------|-------|
| **File** | `app/services/intramural/bacteriologas_cronograma.py` |
| **Action** | Add `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` to existing import tuple |
| **Lines** | 20–24 (existing `from app.constants.urgencias import (...)`) |
| **Change description** | Insert `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA,` after `FACTURADORES_URGENCIAS,` (alphabetical order within the tuple). |
| **Exact diff** | ```diff
 from app.constants.urgencias import (
     EXCEPCIONES_BACTERIOLOGA,
     FACTURADORES_URGENCIAS,
+    PROFESIONALES_EXCEPTUADOS_CRONOGRAMA,
     PROFESIONALES_URGENCIAS,
 )
``` |
| **Verification** | Run the module: `python -c "from app.services.intramural.bacteriologas_cronograma import detect_bacteriologas_cronograma; print('OK')"` — no ImportError |

---

### T3 — Add exception check logic in `detect_bacteriologas_cronograma()`

| Field | Value |
|-------|-------|
| **File** | `app/services/intramural/bacteriologas_cronograma.py` |
| **Action** | Insert new `if` block with `continue` |
| **Insert after** | Line 306 (the `continue` after `"no es una bacterióloga"` error block) |
| **Before** | Line 308 (comment `# ── Determine siglas_filter based on responsable_cierra ──`) |
| **Change description** | After confirming the professional IS a BACTERIOLOGA (lines 291–306), check if `codigo_prof` is in `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA`. If yes, `continue` — skip all cronograma validation for this row. |
| **Exact code to insert** | ```python
        # ★ PROFESIONALES_EXCEPTUADOS_CRONOGRAMA — bypass total de cronograma
        if codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA:
            continue
``` |
| **Important** | Insert AFTER line 306's `continue` (end of the "no es una bacterióloga" block), BEFORE line 308 (the `# ── Determine siglas_filter` comment). There should be a blank line before the new block. |
| **Verification** | See T4 tests. Manual: run `detect_bacteriologas_cronograma` with a row containing `codigo_prof="02217"` and no cronograma match — assert no errors. |

---

### T4 — Add `TestProfesionalesExceptuados` test class

| Field | Value |
|-------|-------|
| **File** | `tests/services/test_intramural_bacteriologas_cronograma.py` |
| **Action** | Append new test class at end of file (after line 1252) |
| **Change description** | Add `class TestProfesionalesExceptuados` with 4 test methods covering MADROÑERO sin cronograma (no error), MADROÑERO con cronograma (no error), otra bacterióloga sin cronograma (sí error), and MADROÑERO con FACTURADORES_URGENCIAS bypass (no error — regression guard). |
| **Tests included** | |
| | **T4.1** — `test_madronero_sin_cronograma_no_error`: `codigo_prof="02217"`, `get_turno_del_dia` returns only another bacterióloga → assert `result == []` |
| | **T4.2** — `test_madronero_con_cronograma_no_error`: `codigo_prof="02217"`, `get_turno_del_dia` returns MADROÑERO → assert `result == []` |
| | **T4.3** — `test_otra_bacteriologa_sin_cronograma_si_error`: `codigo_prof="03374"`, `get_turno_del_dia` returns empty → assert 1 error with "no está en el cronograma" |
| | **T4.4** — `test_madronero_no_bacteriologa_no_bypass` (optional): skip if existing no-BACTERIOLOGA test already covers this path |
| **Mock strategy** | `monkeypatch.setattr("app.services.intramural.bacteriologas_cronograma.get_turno_del_dia", ...)` — same as existing tests |
| **Verification** | `cd tests && pytest services/test_intramural_bacteriologas_cronograma.py::TestProfesionalesExceptuados -v` — all 4 tests pass. Also run full test suite to confirm no regressions: `cd tests && pytest services/test_intramural_bacteriologas_cronograma.py -v` |

---

## Verification Checklist (post-implementation)

- [ ] T1: `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` exists in `app/constants/urgencias.py` as `frozenset({"02217"})`
- [ ] T2: Import resolves without error
- [ ] T3: Code `codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA: continue` placed after BACTERIOLOGA type gate, before `responsable_cierra` logic
- [ ] T4: All tests green, no regressions
- [ ] All scenarios from spec pass (MADROÑERO sin cronograma, MADROÑERO con cronograma, otra bacterióloga, profesional no BACTERIOLOGA)
