# Proposal: Duplicados Farmacia en Urgencias

## Intent

Detectar filas duplicadas en una misma factura con tarifario "Suminstros, Medicamentos" donde se repite el par (Código, Cantidad). Marcar para revisión posibles errores de digitación.

## Scope

### In Scope
- Nuevo detector `duplicados_farmacia.py` en urgencias (SRP, O(n) con dict grouping)
- Integración en `detect_all.py` como llamada + paso a normalized rows
- Nueva sección en `build_urgencias_normalized_rows` con tipo_error "Duplicados Farmacia"
- Tests del detector (sin duplicados, con duplicados, tarifario no farmacia, columna faltante)
- Solo aplica a Urgencias (NO transversales)

### Out of Scope
- No cambiar `ruta_duplicada` en transversales (ese es otro problema: pacientes con múltiples facturas en PyP)
- No agregar auto-corrección ni merge de filas
- No aplicar a odontología ni equipos básicos
- No modificar template HTML (normalized rows ya renderiza automáticamente)

## Capabilities

### New Capabilities
- `duplicados-farmacia`: Si Tarifario = "Suminstros, Medicamentos" y existe el mismo par (factura, código, cantidad) en ≥2 filas → marca duplicado.

### Modified Capabilities
- None

## Approach

1. Crear `app/services/urgencias/duplicados_farmacia.py` con función `detect_duplicados_farmacia(data_sheet, indices) → list[dict]`
2. Firm: recorre filas, filtra por `VALOR_TARIFARIO_FARMACIA`, agrupa por (factura, codigo, cantidad), retorna items con count > 1
3. Importar en `detect_all.py` bajo sección 5 (detectores urgencias), loggear resultado, pasar a normalized_rows
4. En `normalized_rows.py`, agregar parámetro `duplicados_farmacia` y sección de normalización con tipo_error "Duplicados Farmacia"
5. Tests en `tests/services/test_duplicados_farmacia.py`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/urgencias/duplicados_farmacia.py` | New | Detector standalone |
| `app/services/urgencias/detect_all.py` | Modified | Import + call + log + pasar a normalized |
| `app/services/urgencias/normalized_rows.py` | Modified | Nuevo parámetro + sección |
| `tests/services/test_duplicados_farmacia.py` | New | Tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Columna tarifario faltante → graceful return [] | Low | Check None en indices, retorna [] |
| Falsos positivos (mismo código+cantidad es válido) | Medium | Marcar como "Revisión Necesaria", no auto-error |
| Performance O(n) con dict | Low | Negligible para volúmenes típicos |

## Rollback Plan

Revert commits en orden inverso: `normalized_rows.py` → `detect_all.py` → eliminar `duplicados_farmacia.py`. Sin cambios en esquema DB ni endpoints.

## Dependencies

- `VALOR_TARIFARIO_FARMACIA` ya existe en `app/constants/urgencias.py` (= "Suminstros, Medicamentos")
- Columnas `numero_factura`, `codigo`, `cantidad`, `tarifario` ya mapeadas en índices

## Success Criteria

- [ ] Detector retorna lista vacía cuando no hay duplicados
- [ ] Detector encuentra pares (factura, código, cantidad) repetidos con tarifario farmacia
- [ ] Detector ignora filas con tarifario ≠ farmacia
- [ ] Detector retorna [] cuando falta columna tarifario
- [ ] Errores aparecen en UI agrupados como "Duplicados Farmacia"
- [ ] `pytest -v` pasa sin regresiones
