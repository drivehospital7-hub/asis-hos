# Tasks: Reorganización de Módulos

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2500 added + ~6267 deleted = ~8767 total |
| 400-line budget risk | **High** |
| Chained PRs recommended | **Yes** |
| Suggested split | 7 stacked PRs to main (una por fase) |
| Delivery strategy | `ask-on-risk` |
| Chain strategy | `stacked-to-main` |

```
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | Likely PR | Base | Notes |
|------|------|-----------|------|-------|
| 1 | constants/ package | PR 1 | main | ~800 lines; foundation for all imports |
| 2 | transversales/ nuevos | PR 2 | main | ~330 lines; extract parametrized modules |
| 3 | transversales/ unificar | PR 3 | main | ~100 lines; merge decimales, adopt tipo_doc |
| 4 | odontologia/ | PR 4 | main | ~370 lines; extract + detect_all |
| 5 | urgencias/ | PR 5 | main | ~950 lines; **biggest risk**, split centro_costo |
| 6 | equipos_basicos/ | PR 6 | main | ~120 lines; reuses transversales |
| 7 | Cleanup | PR 7 | main | ~50 changed + ~6267 deleted; final switch |

---

## Phase 1: constants/ package

- [x] **T-01** — Create `constants/base.py`, `columnas.py`, `colores.py`
  - Desc: Crear directorio `constants/`, extraer constantes base (sheets, sufijos, áreas), columnas (COLUMNS_TO_KEEP, URGENCIA_COLUMNS_TO_KEEP), colores UI (COLOR_*, HEADER_*). Módulos individuales con su contenido exacto de `constants.py`.
  - Deps: —
  - Files: `app/constants/__init__.py`, `app/constants/base.py`, `app/constants/columnas.py`, `app/constants/colores.py`
  - ~300 líneas
  - Riesgo: Bajo
  - Éxito: ✅ `from app.constants import ALLOWED_EXCEL_SUFFIXES, COLUMNS_TO_KEEP` funciona

- [x] **T-02** — Create `constants/odontologia.py`, `urgencias.py`
  - Desc: Extraer constantes por dominio. Odontología: PYP_CUPS_CODES, profesionales, IDE Contrato PyP, thresholds, equipos básicos. Urgencias: IDE Contrato ~30 reglas, centros costo, SOAT, CAPITA, hospitalización, equivalencias.
  - Deps: T-01
  - Files: `app/constants/odontologia.py`, `app/constants/urgencias.py`, `app/constants/columnas.py` (EB headers/columns), `app/constants/__init__.py` (re-export)
  - ~800 líneas
  - Riesgo: Bajo (extracción mecánica 1:1)
  - Éxito: ✅ `from app.constants.urgencias import IDE_CONTRATO_906340_ESSC18` funciona; todos los imports existentes en servicios resueltos

- [ ] **T-03** — Wire `constants/__init__.py` as facade + delete `constants.py`
  - Desc: Renombrar `app/constants.py` a backup (plan de rollback), verificar que `constants/__init__.py` re-exporta ABSOLUTAMENTE TODO. Ejecutar `pytest tests/` y probar import desde cada servicio que usa `from app.constants import X`.
  - Deps: T-02
  - Files: `app/constants.py` (delete/rename), `app/constants/__init__.py` (final re-export)
  - ~80 líneas
  - Riesgo: Medio (ruptura de imports si __init__.py omite algún símbolo)
  - Éxito: `pytest tests/` pasa sin cambios en los tests; `python -c "from app.constants import *"` no arroja error

---

## Phase 2: transversales/ nuevos

- [x] **T-04** — Create `transversales/column_indices.py`
  - Desc: Extraer `_get_column_indices` de `revision_sheet.py` a nuevo módulo. Copia exacta (se eliminará la original en Fase 7). Agregar test unitario.
  - Deps: T-03
  - Files: `app/services/transversales/column_indices.py` (new), `app/services/transversales/__init__.py` (re-export), `tests/services/test_column_indices.py` (new)
  - ~80 líneas + tests
  - Riesgo: Bajo
  - Éxito: `test_column_indices.py` pasa; misma salida que original
  - **Nota**: El archivo se llamó `doble_tipo_procedimiento.py` (no `doble_tipo.py` como sugería el plan) para mantener consistencia con el nombre de la función.

- [x] **T-05** — Create `transversales/doble_tipo_procedimiento.py`
  - Desc: Extraer `_detect_doble_tipo_procedimiento`. Función autónoma, sin dependencia de área.
  - Deps: T-03
  - Files: `app/services/transversales/doble_tipo_procedimiento.py` (new), `app/services/transversales/__init__.py` (re-export), `tests/services/test_doble_tipo_procedimiento.py` (new)
  - ~60 líneas + tests
  - Riesgo: Bajo
  - Éxito: test pasa con casos: factura con 2 tipos diferentes → detectado; factura con 1 tipo → ignorado

- [x] **T-06** — Create `transversales/ruta_duplicada.py` (parametrizado)
  - Desc: Unificar `_detect_ruta_duplicada` (odontología, threshold=3) y `_detect_ruta_duplicada_equipos_basicos` (threshold distinto) en UNA función con parámetro `threshold: int = 3`. Agregar tests para ambos thresholds.
  - Deps: T-03
  - Files: `app/services/transversales/ruta_duplicada.py` (new), `app/services/transversales/__init__.py` (re-export), `tests/services/test_ruta_duplicada.py` (new)
  - ~71 líneas + tests
  - Riesgo: Medio (parametrización cambia firma)
  - Éxito: test con threshold=3 detecta ≥3 facturas; test con threshold=2 detecta ≥2; convenios no-PyP ignorados

- [x] **T-07** — Create `transversales/cantidades_anomalas.py` (parametrizado)
  - Desc: Unificar `_detect_cantidades_anomalas` y `_detect_cantidades_anomalas_equipos_basicos`. Parámetros: `cantidad_consultas_min: int = 2`, `cantidad_max_general: int = 10`, `cantidad_pyp_min: int = 3`.
  - Deps: T-03
  - Files: `app/services/transversales/cantidades_anomalas.py` (new), `app/services/transversales/__init__.py` (re-export), `tests/services/test_cantidades_anomalas.py` (new)
  - ~91 líneas + tests
  - Riesgo: Medio
  - Éxito: tests para consultas ≥2, general >10, PyP ≥3; ambas áreas (odonto/EB) usando misma función

---

## Phase 3: Unificar transversales

- [x] **T-08** — Merge `transversales/decimales.py` → `_detect_decimals` delega a `detect_decimales`
  - Desc: La versión transversales retorna `list[str]` (solo facturas). La versión inline retorna `list[dict]` con `factura` + `valores`. Unificar en transversales: `detect_decimales` retorna `list[dict]`. Actualizar todos los consumidores en `detect_all_problems` (odontología, urgencias, EB). Mantener compatibilidad con la versión anterior si hay otros consumidores.
  - Deps: T-07
  - Files: `app/services/transversales/decimales.py` (modify), `app/services/revision_sheet.py` (update calls)
  - ~60 líneas
  - Riesgo: Medio (cambio de formato afecta templates y detect_all)
  - Éxito: misma salida que antes con Excel de prueba; tests existentes pasan

- [x] **T-09** — Adopt `transversales/tipo_documento_edad.py` como única versión
  - Desc: La transversales ya tiene versión superior (mejor parsing, más campos, tipos adicionales NIP/NIT/PAS/PE/SC). Eliminar `_detect_tipo_identificacion_edad` de `revision_sheet.py` (línea 581). Routear llamadas de `detect_all_problems` a transversales.
  - Deps: T-07
  - Files: `app/services/revision_sheet.py` (delete inline function, update callers)
  - ~40 líneas
  - Riesgo: Bajo (transversales es strictly better)
  - Éxito: mismas detecciones; no hay más duplicación de esta regla

---

## Phase 4: odontologia/

- [ ] **T-10** — Create `odontologia/profesionales.py`, `centro_costo.py`, `ide_contrato.py`
  - Desc: Extraer las 3 funciones específicas de odontología desde `revision_sheet.py`. Copia exacta 1:1. Cada función independiente sigue firma `def detect_*(data_sheet, indices, **kwargs) → list[dict]`.
  - Deps: T-09
  - Files: `app/services/odontologia/__init__.py` (new), `app/services/odontologia/profesionales.py` (new), `app/services/odontologia/centro_costo.py` (new), `app/services/odontologia/ide_contrato.py` (new), `tests/services/odontologia/test_profesionales.py` (new)
  - ~250 líneas
  - Riesgo: Bajo (copia exacta)
  - Éxito: import de `odontologia.profesionales.detect_profesionales_odontologia` funciona

- [ ] **T-11** — Create `odontologia/detect_all.py` + wire into `revision_sheet.py`
  - Desc: Nuevo orquestador que llama transversales + odontología modules. MODIFICAR `revision_sheet.py::detect_all_problems` en la rama `area == ODONTOLOGIA` para delegar a `odontologia.detect_all`. Ambos caminos coexisten (viejo código inline aún presente pero inactivo para odonto).
  - Deps: T-10
  - Files: `app/services/odontologia/detect_all.py` (new), `app/services/revision_sheet.py` (modify dispatcher)
  - ~120 líneas
  - Riesgo: Medio (dispatcher toca lógica de negocio)
  - Éxito: mismo output con archivo Excel de odontología de prueba

---

## Phase 5: urgencias/

- [ ] **T-12** — Create urgencias/ low-risk modules: `mal_capitado`, `profesionales`, `revision`, `codigos_db`, `ide_contrato_reverse`, `cantidades`
  - Desc: Extraer funciones independientes y autónomas desde `revision_sheet.py`. Cada una en su propio archivo con tests. Son las funciones de comportamiento simple (sin dependencias entre sí) que hacen una cosa bien definida.
  - Deps: T-09
  - Files: `app/services/urgencias/__init__.py` (new), `*mal_capitado.py`, `*profesionales.py`, `*revision.py`, `*codigos_db.py`, `*ide_contrato_reverse.py`, `*cantidades.py`, +tests
  - ~300 líneas
  - Riesgo: Bajo (funciones autónomas)
  - Éxito: imports OK; tests con datos mínimos pasan

- [ ] **T-13** — Create urgencias/ high-risk modules: `centro_costo`, `ide_contrato`, `cups_equivalentes`, `sala_observacion`, `hospitalizacion`
  - Desc: **La tarea más crítica del refactor.** Extraer 5 módulos desde `_detect_centro_costo_urgencias` (~1800 líneas que hace 5+ cosas en un solo loop). ESTRATEGIA: (1) Identificar cada sub-regla en el loop original, (2) Copiar el loop completo a cada módulo, (3) Eliminar las líneas de otras reglas de cada copia, (4) Refactorizar cada copia para que sea autónoma. NO refactorizar la lógica interna — solo separar. Preservar TODOS los logs exactos.
  - Deps: T-12
  - Files: `app/services/urgencias/centro_costo.py`, `ide_contrato.py`, `cups_equivalentes.py`, `sala_observacion.py`, `hospitalizacion.py` + tests
  - ~600 líneas
  - Riesgo: **Alto** (lógica entrelazada en el loop original, alto riesgo de regresión)
  - Éxito: mismo output que original con Excel de urgencias real. Comparar archivo generado con línea base de producción.
  - Notas: Se recomienda tener un archivo Excel real de urgencias con casos conocidos para validar. Validar CONTRA el original antes de Phase 7. Los tests deben incluir casos de borde: centro costo, IDE contrato, cups equivalentes, sala observación (>6h/≤6h), hospitalización (SOAT/no-SOAT).

- [ ] **T-14** — Create `urgencias/detect_all.py` + wire into `revision_sheet.py`
  - Desc: Orquestador de urgencias que llama transversales + 11 módulos. MODIFICAR `revision_sheet.py::detect_all_problems` en rama `area == URGENCIAS` para delegar. El loop original de _detect_centro_costo_urgencias se reemplaza por 5 llamadas separadas a los nuevos módulos.
  - Deps: T-13
  - Files: `app/services/urgencias/detect_all.py` (new), `app/services/revision_sheet.py` (modify dispatcher)
  - ~150 líneas
  - Riesgo: Alto (el dispatcher de urgencias es el más complejo)
  - Éxito: mismo output que producción; `_build_urgencias_normalized_rows` invocado correctamente

---

## Phase 6: equipos_basicos/

- [ ] **T-15** — Create `equipos_basicos/profesionales.py` + `detect_all.py` + wire
  - Desc: Módulo de profesionales EB (similar a odontología pero con diferentes constantes). Orquestador reusa transversales parametrizados (ruta_duplicada con threshold EB, cantidades_anomalas con constantes EB). MODIFICAR `revision_sheet.py` dispatcher para delegar.
  - Deps: T-11, T-14
  - Files: `app/services/equipos_basicos/__init__.py` (new), `*profesionales.py`, `*detect_all.py` (new), `app/services/revision_sheet.py` (modify dispatcher), tests
  - ~120 líneas
  - Riesgo: Bajo (ya parametrizado en transversales, solo constantes distintas)
  - Éxito: mismo output; ruta_duplicada usa threshold EB; cantidades_anomalas usa constantes EB

---

## Phase 7: Cleanup

- [ ] **T-16** — Update `exporter.py` imports + delete `revision_sheet.py` + update tests
  - Desc: Cambiar `from app.services.revision_sheet import detect_all_problems` por los nuevos orquestadores de área en `exporter.py`. Eliminar `app/services/revision_sheet.py` (6267 líneas menos). Actualizar `tests/services/test_revision_sheet.py` para importar desde nuevos módulos. Eliminar `detect_all_problems` remanente y cualquier código inline que ya esté delegado.
  - Deps: T-15
  - Files: `app/services/exporter.py` (modify imports), `app/services/revision_sheet.py` (DELETE), `tests/services/test_revision_sheet.py` (update imports)
  - ~50 changed + ~6267 deleted
  - Riesgo: Medio (imports rotos si algún consumidor no se actualizó)
  - Éxito: `pytest tests/` pasa; `python -c "from app.services.exporter import export_excel_with_cruce_facturas"` funciona; Excel real procesado con misma salida que antes
  - Notas: Buscar con `grep -r "revision_sheet" app/` cualquier import remanente antes de eliminar. Si se encuentra algún import en routes/, control_errores, etc., actualizarlo también.
