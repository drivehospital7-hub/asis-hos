# Proposal: Duplicados Farmacia para tipo factura Farmacia (sin tarifario ni tipo procedimiento)

## Intent

Extender la lógica de detección de duplicados de farmacia (actualmente solo Urgencias) al tipo factura "Farmacia", eliminando los filtros de tarifario y codigo_tipo_procedimiento que no aplican. Aprovechar para extraer el algoritmo común a una función parametrizada reutilizable.

## Scope

### In Scope
- Crear detector `detect_duplicados_farmacia_farmacia` en `app/services/farmacia/`
- Extraer algoritmo común a `app/services/transversales/detect_duplicados_base.py` (parametrizado por tipo_factura, tarifario opcional, codigos_tipo_proc opcional)
- Refactorizar `detect_duplicados_farmacia` (Urgencias) para usar la función base (sin cambio de comportamiento)
- Registrar el nuevo detector en `_get_farmacia_detectors()` de `app/services/farmacia/detect_all.py`
- Agregar el error group "Duplicados Farmacia" al mapeo de Farmacia en `detect_all.py` y al handler en `normalized_rows.py` (ya soporta estructura)

### Out of Scope
- Cambiar comportamiento del detector de Urgencias existente
- Modificar estructura del spec `duplicados-farmacia` (solo se agrega delta)
- Interfaz de usuario o frontend

## Capabilities

### New Capabilities
- `duplicados-farmacia-farmacia`: Detección de duplicados para tipo factura "Farmacia" — agrupa por factura (sin tarifario ni codigo_tipo_procedimiento). Si todos los pares (codigo, cantidad) aparecen ≥2 veces, se marca la factura completa.

### Modified Capabilities
- `duplicados-farmacia`: El detector de Urgencias se refactoriza internamente para usar la función base compartida. No cambia comportamiento externo. Se agregará delta spec documentando la refactorización.

## Approach

1. Crear `app/services/transversales/detect_duplicados_base.py` con función `detect_duplicados_generico(data_sheet, indices, *, tipo_factura, tarifario_val=None, codigos_tipo_proc=None)` que implementa el algoritmo central
2. Refactorizar `duplicados_farmacia.py` (Urgencias) para llamar a la función base con `tipo_factura="Urgencias"`, `tarifario_val=VALOR_TARIFARIO_FARMACIA`, `codigos_tipo_proc=CODIGOS_TIPO_PROC_09_12`
3. Crear `app/services/farmacia/duplicados_farmacia_farmacia.py` que llama a la función base con `tipo_factura="Farmacia"` (sin tarifario ni códigos)
4. Registrar en `_get_farmacia_detectors()` y en `detect_all_problems_farmacia()`
5. El handler "Duplicados Farmacia" en `normalized_rows.py` ya soporta el output — validar que funcione sin `codigo_tipo_procedimiento`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/transversales/detect_duplicados_base.py` | **New** | Algoritmo compartido parametrizado |
| `app/services/urgencias/duplicados_farmacia.py` | Modified | Refactorizado para usar función base |
| `app/services/farmacia/duplicados_farmacia_farmacia.py` | **New** | Detector específico de Farmacia |
| `app/services/farmacia/detect_all.py` | Modified | Registrar nuevo detector + error group |
| `app/tipo_factura_registry.py` | None | Ya usa `_get_farmacia_detectors()` |
| `app/services/normalized_rows.py` | Modified | Ajustar handler "Duplicados Farmacia" si es necesario |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Refactor rompe Urgencias existente | Low | Tests existentes + misma lógica envuelta |
| Columnas faltantes en Farmacia (codigo_tipo_procedimiento) | Low | Función base tolera columnas opcionales |

## Rollback Plan

Revert solo el nuevo detector + refactor: restaurar `duplicados_farmacia.py` original, eliminar `detect_duplicados_base.py`, quitar registro de Farmacia.

## Dependencies

- Ninguna externa. Depende de `normalize_invoice` y constantes existentes.

## Success Criteria

- [ ] Detector de Urgencias produce EXACTAMENTE los mismos resultados antes y después del refactor
- [ ] Nuevo detector de Farmacia detecta facturas con todos los pares (codigo, cantidad) duplicados
- [ ] Sin tarifario filter: se evalúan TODAS las filas de tipo Farmacia
- [ ] Sin codigo_tipo_procedimiento filter: se agrupa solo por factura
- [ ] Errores se renderizan correctamente en la tabla de resultados
