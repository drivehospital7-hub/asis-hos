# Proposal: Cerradas Toggle — Ordenado y Facturado

## Intent

Usuario necesita filtrar facturas "abiertas" (sin `Fecha Cierre`) del cruce
Ordenado vs Facturado. Por defecto mantiene el comportamiento actual. Un
checkbox "Cerradas" excluye del resultado los registros sin fecha de cierre.

## Scope

### In Scope

- Checkbox "Cerradas" en UI frontend
- Parámetro `cerradas: bool = False` en `procesar_cruce()`
- Filtro: excluir del `no_facturados` los registros con `Fecha Cierre` vacío
  cuando `cerradas=True`
- Header `Fecha Cierre` debe ser opcional (no romper si la columna no existe)
- Tests para el filtro

### Out of Scope

- No se modifica la lógica de matching o agregación existente
- No se persiste el estado del checkbox entre sesiones
- No se agrega filtro por rango de fechas

## Capabilities

### New Capabilities

None — toggle sobre funcionalidad existente.

### Modified Capabilities

None — no hay spec principal de `ordenado-facturado` en `openspec/specs/`.
Solo existe un delta spec en otro cambio activo (`filtrar-codigos-procesados`)
que aún no se ha archivado.

## Approach

1. **Service** (`app/services/ordenado_facturado_service.py`):
   Agregar `cerradas: bool = False` a `procesar_cruce()`. Al leer ayudas,
   detectar columna `Fecha Cierre` como header opcional. Cuando `cerradas=True`,
   construir set de facturas con `Fecha Cierre` vacío y filtrar del
   `no_facturados` antes de retornar.

2. **Route** (`app/routes/ordenado_facturado.py`):
   Leer `cerradas` del form data (`request.form.get("cerradas") == "true"`),
   pasarlo a `procesar_cruce()`.

3. **Frontend** (`frontend/src/pages/ordenado-facturado/page.tsx`):
   Agregar checkbox "Cerradas" en el formulario. Incluir en el FormData como
   `cerradas: "true"` o ausente.

4. **Tests** (`tests/services/test_ordenado_facturado_service.py`):
   Agregar tests: filtro con cerradas activo, filtro con cerradas inactivo,
   columna faltante no rompe, valores nulos/manejos de borde.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/ordenado_facturado_service.py` | Modified | `procesar_cruce()` parámetro + filtro |
| `app/routes/ordenado_facturado.py` | Modified | Leer `cerradas` del form |
| `frontend/src/pages/ordenado-facturado/page.tsx` | Modified | Checkbox + FormData |
| `tests/services/test_ordenado_facturado_service.py` | Modified | Tests del filtro |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Columna `Fecha Cierre` no existe en ayudas | Low | Header opcional, skip sin error |
| Falso positivo si valor vacío es string `""` vs null | Low | Chequear ambos |

## Rollback Plan

Revertir cambios en los 4 archivos a HEAD. Un solo commit atómico.

## Dependencies

Ninguna.

## Success Criteria

- [ ] Checkbox presente en UI, desactivado por defecto
- [ ] Con checkbox OFF: mismos resultados que antes
- [ ] Con checkbox ON: registros sin `Fecha Cierre` excluidos
- [ ] `Fecha Cierre` ausente no produce error
- [ ] Tests pasan
