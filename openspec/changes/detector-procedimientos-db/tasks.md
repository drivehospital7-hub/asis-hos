# Tasks: Detector transversal de procedimientos contratados

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~247 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Decision needed before apply | Yes |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low
```

## Phase 1: Core Detector

- [ ] **1.1** Crear `app/services/transversales/procedimiento_contratado.py` con `detect_cups_sin_contrato(data_sheet, indices) -> list[dict]`: pre-load query JOIN 5 tablas → set de pares válidos + dict de nombres EPS; row-by-row scan normalizando con `.strip().upper()`; try/except DB con retorno `[]`
- [ ] **1.2** Modificar `app/services/transversales/__init__.py`: agregar `from .procedimiento_contratado import detect_cups_sin_contrato` + exportar en `__all__`

## Phase 2: Normalización a filas uniformes

- [ ] **2.1** Modificar `app/services/normalized_rows.py`: agregar bloque `Cups Sin Contrato` en `build_normalized_rows()` — itera `error_groups.get("Cups Sin Contrato", [])`, mapea a fila con `tipo_error`, `descripcion` del problema, `procedimiento` = código + nombre, `detalle` = entidad
- [ ] **2.2** Modificar `app/services/odontologia/normalized_rows.py`: agregar parámetro opcional `cups_sin_contrato: list[dict] | None = None` en `build_odontologia_normalized_rows()` + bloque que genera mismas filas que 2.1

## Phase 3: Integración en detect_all.py de cada área

- [ ] **3.1** Modificar `app/services/urgencias/detect_all.py`: importar `detect_cups_sin_contrato`, llamar después de detectores transversales, agregar a `error_groups["Cups Sin Contrato"]`, agregar a `resultado["problemas"]` y `resultado["totales"]`
- [ ] **3.2** Modificar `app/services/hospitalizacion/detect_all.py`: ídem 3.1
- [ ] **3.3** Modificar `app/services/intramural/detect_all.py`: ídem 3.1
- [ ] **3.4** Modificar `app/services/ambulatoria/detect_all.py`: ídem 3.1
- [ ] **3.5** Modificar `app/services/odontologia/detect_all.py`: importar `detect_cups_sin_contrato`, llamar, pasar resultado como `cups_sin_contrato=` a `build_odontologia_normalized_rows()`, agregar a `resultado["problemas"]` y `resultado["totales"]`
- [ ] **3.6** Modificar `app/services/equipos_basicos/detect_all.py`: ídem 3.5

## Phase 4: Tests

- [ ] **4.1** Crear `tests/services/test_transversales_procedimiento_contratado.py`: mockear `SessionLocal` con fixture de 3 pares válidos; probar happy path (fila válida → []), CUPS no contratado (1 error con mensaje correcto), DB offline (monkeypatch Exception → []), columna `codigo_entidad_cobrar` faltante (indices None → []), normalización strip/upper (fila con espacios → match)
