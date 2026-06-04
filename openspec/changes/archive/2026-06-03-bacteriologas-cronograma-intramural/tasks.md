# Tasks: Bacteriólogas con Cronograma en Intramural

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~410 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Detector + integración + tests | Single PR | Cambio autocontenido, ~410 líneas estimadas |

## Phase 1: Detector Module

- [x] 1.1 Crear `app/services/intramural/bacteriologas_cronograma.py` — función `_parse_fecha(val) -> date | None` que maneje ISO string, serial Excel, string local `dd/mm/aaaa`, None, e inválidos con log warning
- [x] 1.2 Implementar `detect_bacteriologas_cronograma(data_sheet, indices) -> list[dict]` con los filtros: tipo_factura_descripcion == "Intramural", codigo_tipo_procedimiento in ("02","05"), laboratorio == "Si"
- [x] 1.3 Implementar lookup en `PROFESIONALES_URGENCIAS`: si no existe → error, si tipo != "BACTERIOLOGA" → error, si es BACTERIOLOGA → continuar
- [x] 1.4 Implementar excepciones: skip si `codigo` in `EXCEPCIONES_BACTERIOLOGA` ({"904903", "903883"})
- [x] 1.5 Integrar validación contra cronograma: parsear fec_factura → `get_turno_del_dia(mes, anio, dia)`, si `[]` → skip, si codigo_profesional no está en turnos → error
- [x] 1.6 Implementar deduplicación: set `facturas_con_error` para máximo 1 error por factura

## Phase 2: Integration in detect_all.py

- [x] 2.1 Importar `detect_bacteriologas_cronograma` en `app/services/intramural/detect_all.py`
- [x] 2.2 Agregar detector a `_get_intramural_detectors()`
- [x] 2.3 En `detect_all_problems_intramural()`: llamar detector, agregar a `error_groups["Profesionales"]`, `resultado["problemas"]["profesionales"]`, `resultado["totales"]["profesionales"]`

## Phase 3: Testing

- [x] 3.1 Crear `tests/services/test_intramural_bacteriologas_cronograma.py` con tests parametrizados para `_parse_fecha`: ISO string, serial Excel, local string, None, valor inválido
- [x] 3.2 Escribir pruebas para `detect_bacteriologas_cronograma`: skip no Intramural, skip wrong tipo, skip lab != "Si", skip excepción, skip cronograma vacío, skip fecha inválida, profesional no encontrado, profesional no bacterióloga, bacterióloga fuera de cronograma, happy path en cronograma, dedup por factura
- [x] 3.3 Verificar: `python -m pytest tests/services/test_intramural_bacteriologas_cronograma.py -v` y test de detect_all no se rompe: `python -m pytest tests/services/test_intramural_detect_all.py -v`
