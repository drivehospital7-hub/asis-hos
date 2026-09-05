# Delta for Intramural Detection

## ADDED Requirements

### Requirement: R6 — Tipo Identificación Entidad Detector

The Intramural orchestrator MUST call `detect_tipo_identificacion_entidad` as a transversal detector alongside existing transversal rules (decimales, tipo_documento_edad, codigo_entidad_vs_afiliacion, tipo_usuario). The call result MUST be included in `error_groups`, `resultado["problemas"]`, and `resultado["totales"]`.

#### Scenario: Detector importado y llamado

- GIVEN `app/services/intramural/detect_all.py`
- WHEN the file is executed
- THEN `detect_tipo_identificacion_entidad` is imported from `app.services.transversales`
- AND `tipo_identificacion_entidad = detect_tipo_identificacion_entidad(data_sheet, indices)` is called in section 1 (transversales)
- AND the result is not modified — raw list from detector preserved

#### Scenario: Error group incluido

- GIVEN the `error_groups` dict in `build_normalized_rows`
- WHEN the dict is built
- THEN it contains key `"Código Entidad vs Afiliación"` with value `tipo_identificacion_entidad`

#### Scenario: Resultado y totales actualizados

- GIVEN the `resultado` dict returned by the orchestrator
- WHEN inspection is performed
- THEN `resultado["problemas"]["tipo_identificacion_entidad"]` equals the detector's output list
- AND `resultado["totales"]["tipo_identificacion_entidad"]` equals `len(tipo_identificacion_entidad)`
