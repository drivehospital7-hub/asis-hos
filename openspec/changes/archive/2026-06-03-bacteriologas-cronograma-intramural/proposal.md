# Proposal: Bacteriólogas con cronograma en Intramural

## Intent

Validar que facturas Intramural con `Tipo=02/05` + `Laboratorio=Si` tengan como `Código Profesional` una bacterióloga que esté en el cronograma del día según `Fec. Factura`. Esto cierra un gap: la regla existente en Urgencias no se aplica a Intramural.

## Scope

### In Scope

1. Nuevo detector `app/services/intramural/bacteriologas_cronograma.py`
2. Registro en `_get_intramural_detectors()` en `detect_all.py`
3. Integración en `error_groups` del orquestador (`detect_all.py`)
4. Parseo de `Fec. Factura` → mes/año/día para `get_turno_del_dia(mes, anio, dia)`
5. Excepciones `EXCEPCIONES_BACTERIOLOGA` (904903, 903883) — saltar sin error
6. Cronograma inexistente (retorna `[]`) → saltar sin error

### Out of Scope

- Modificar el cronograma service o `PROFESIONALES_URGENCIAS`
- Modificar `normalized_rows.py` (usa "Profesionales" key ya soportada)
- Modificar detectores de Urgencias
- Validación cruzada entre múltiples filas de misma factura

## Capabilities

### New Capabilities

- `intramural-bacteriologas-cronograma`: Validación de bacteriólogas en Intramural contra cronograma diario, con filtro Tipo=02/05 + Lab=Si + excepciones

### Modified Capabilities

None — nueva regla, no cambia specs existentes.

## Approach

1. **Nuevo detector** `bacteriologas_cronograma.py`: itera filas filtrando `Intramural` + `Tipo Procedimiento in (02,05)` + `Laboratorio=Si`. Para cada una: verifica `Código Profesional` en `PROFESIONALES_URGENCIAS` con tipo `BACTERIOLOGA`; salta si código in `EXCEPCIONES_BACTERIOLOGA`; parsea `Fec. Factura` para obtener mes, año, día; llama `get_turno_del_dia(mes, anio, dia)`; si cronograma retorna `[]` → skip; si el código no está en los turnos → error.
2. **Registro**: agregar a `_get_intramural_detectors()` y en `detect_all_problems_intramural()` inyectar en `error_groups["Profesionales"]`.
3. **Formato error**: mismo schema que `detect_profesionales_urgencias` (factura, codigo_profesional, nombre, procedimiento, regla, problema, fec_factura, tipo_procedimiento, laboratorio).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/intramural/bacteriologas_cronograma.py` | New | Detector de bacteriólogas vs cronograma |
| `app/services/intramural/detect_all.py` | Modified | Agregar detector a `_get_intramural_detectors()` + `error_groups` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cronograma no existe para ese mes | Med | Detectar y skip silencioso |
| `Fec. Factura` con formato inesperado | Low | Try/except con skip + log warning |
| `codigo_tipo_procedimiento` o `laboratorio` ausente en índices | Low | Check `None` early y skip |

## Rollback Plan

Revertir el commit que toca `detect_all.py` y eliminar `bacteriologas_cronograma.py`. Cambio autocontenido sin side effects en otras áreas.

## Dependencies

- `app/services/cronograma_bacteriologas_service.py` — ya existe
- `app/constants/urgencias.py` (`PROFESIONALES_URGENCIAS`, `EXCEPCIONES_BACTERIOLOGA`) — ya existen

## Success Criteria

- [ ] `_get_intramural_detectors()` incluye `detect_bacteriologas_cronograma`
- [ ] Factura Intramural con Tipo=02 + Lab=Si + bacterióloga fuera del cronograma → error listado
- [ ] Misma factura con excepción (904903) → sin error
- [ ] Cronograma inexistente → sin error
- [ ] Tests unitarios pasan
