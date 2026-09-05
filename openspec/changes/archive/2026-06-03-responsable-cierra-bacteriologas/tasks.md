# Tasks: Responsable Cierra modifica reglas de bacteriólogas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~350-400 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium

## Phase 1: Foundation — Constantes

- [x] **T-01** — Agregar `FACTURADORES_URGENCIAS: set[str]` en `app/constants/urgencias.py` con los 4 nombres del odontología, y agregar `RESPONSABLE_CHAPUEL`, `RESPONSABLE_TAPIA`, `RESPONSABLE_ORDONEZ` en `app/constants/intramural.py`.
  - **Archivos**: `app/constants/urgencias.py`, `app/constants/intramural.py`
  - **Dependencias**: ninguna
  - **CA**: `FACTURADORES_URGENCIAS` es `set[str]` con los 4 nombres exactos; `RESPONSABLE_CHAPUEL`, `RESPONSABLE_TAPIA`, `RESPONSABLE_ORDONEZ` son cadenas UPPER exactas.
  - **Esfuerzo**: bajo

- [x] **T-02** — Migrar import: en `app/services/odontologia/detect_por_responsable.py` eliminar definición local de `FACTURADORES_URGENCIAS` e importarlo desde `app.constants.urgencias`. No cambiar lógica de `_partition_rows`.
  - **Archivos**: `app/services/odontologia/detect_por_responsable.py`
  - **Dependencias**: T-01
  - **CA**: `FACTURADORES_URGENCIAS` referenciado funciona idéntico; `_partition_rows` sin cambios; tests existentes de odontología pasan.
  - **Esfuerzo**: bajo

## Phase 2: Core — Parámetros y lógica

- [x] **T-03** — Agregar `siglas_filter: set[str] | None = None` a `get_turno_del_dia()` en `app/services/cronograma_bacteriologas_service.py`. Cuando es `None`, filtrar CE|PYM (comportamiento actual). Cuando es `set()` (vacío), retornar todos. Cuando es `{"PYM"}`, solo PYM. Cuando es `{"CE"}`, solo CE.
  - **Archivos**: `app/services/cronograma_bacteriologas_service.py`
  - **Dependencias**: ninguna (el parámetro es opcional, compatible hacia atrás)
  - **CA**: `get_turno_del_dia(mes, anio, dia, siglas_filter=None)` retorna igual que antes; `siglas_filter={"PYM"}` solo retorna turnos con "PYM" en código; `siglas_filter={"CE"}` solo CE; `siglas_filter=set()` retorna todos sin filtrar.
  - **Esfuerzo**: bajo

- [x] **T-04** — Modificar `detect_bacteriologas_cronograma()` en `app/services/intramural/bacteriologas_cronograma.py` para aceptar `responsable_cierra: dict[str, str] | None = None`. Insertar bloque de decisión entre validación PROFESIONALES_URGENCIAS (paso 1) y llamada a `get_turno_del_dia`: si responsable está en FACTURADORES_URGENCIAS → skip cronograma (continue); si es CHAPUEL → `siglas_filter={"PYM"}`; si es TAPIA/ORDOÑEZ → `siglas_filter={"CE"}`; else → `siglas_filter=None`.
  - **Archivos**: `app/services/intramural/bacteriologas_cronograma.py`
  - **Dependencias**: T-01, T-03
  - **CA**: Comportamiento default (None/responsable no coincide) = CE|PYM igual que antes; Chapuel → solo PYM; Tapia/Ordoñez → solo CE; FACTURADORES_URGENCIAS → bypass total de cronograma; comparación case-insensitive con `.upper().strip()`.
  - **Esfuerzo**: medio

- [x] **T-05** — En `detect_all_problems_intramural()` en `app/services/intramural/detect_all.py`, pasar `responsable_cierra` a `detect_bacteriologas_cronograma(data_sheet, indices, responsable_cierra)`. El dict ya existe en el orquestador (línea 73).
  - **Archivos**: `app/services/intramural/detect_all.py`
  - **Dependencias**: T-04
  - **CA**: Llamada actualizada; `bacteriologas = detect_bacteriologas_cronograma(data_sheet, indices, responsable_cierra)`; retorno incluye errores según responsable.
  - **Esfuerzo**: bajo

## Phase 3: Tests

- [x] **T-06** — Tests unitarios de `get_turno_del_dia` con `siglas_filter`: mock cronograma JSON con turnos mixtos CE/PYM; verify filtro None, set(), {"PYM"}, {"CE"}.
  - **Archivos**: nuevo test o agregar a test de cronograma_existente
  - **Dependencias**: T-03
  - **CA**: Cada variante de `siglas_filter` retorna los turnos esperados según la regla de negocio.
  - **Esfuerzo**: bajo

- [x] **T-07** — Tests unitarios de `detect_bacteriologas_cronograma` con `responsable_cierra`: mock `get_turno_del_dia` y testear 10 casos del spec (Chapuel+PYM ok, Chapuel+CE error, Tapia+CE ok, Tapia+PYM error, Urgencias bypass ok, Urgencias no encontrado error, default CE|PYM, None fallback, tildes/espacios irregulares, etc.).
  - **Archivos**: `tests/services/test_intramural_bacteriologas_cronograma.py`
  - **Dependencias**: T-04
  - **CA**: Cada escenario del spec produce el resultado esperado (error o sin error).
  - **Esfuerzo**: alto

- [x] **T-08** — Tests de integración: verify que `detect_all_problems_intramural` pasa `responsable_cierra` correctamente al detector (mock `get_turno_del_dia` + agregar columna `responsable_cierra` al workbook). Test de regresión: odontología importa `FACTURADORES_URGENCIAS` desde constants y `_partition_rows` funciona.
  - **Archivos**: `tests/services/test_intramural_bacteriologas_cronograma.py` (extender), y test odontología existente
  - **Dependencias**: T-05, T-02
  - **CA**: Flujo completo desde detect_all con responsable produce errores según regla de negocio; odontología pasa tests de regresión sin cambios en comportamiento.
  - **Esfuerzo**: medio
