# Proposal: Filtro por responsables en Abiertas Urgencias

## Intent

El usuario necesita filtrar la tabla de facturas abiertas por responsable (facturador de turno). Actualmente no existe ningún filtro — se muestran todas las filas siempre. Agregar un `<select>` dinámico que liste solo los responsables presentes en los resultados actuales, permitiendo al usuario enfocarse rápidamente en las facturas de un turno específico.

## Scope

### In Scope
- `<select>` nativo con opciones dinámicas extraídas de `results[].responsable`
- Filtrado inline con `useMemo` antes del render de la tabla
- Opción "Todos" por defecto (sin filtro)
- Integración visual consistente con control-novedades (`h-9 rounded-md border border-input bg-background px-3 text-sm`)
- Los valores atípicos ("Sin Egreso", "—", "Sin cronograma", etc.) aparecen en el dropdown

### Out of Scope
- No cambios en backend, DB, ni API
- No cambios en el cronograma/schedule
- No cambios en `utils.ts` (salvo que se decida modificar `copiarResultados`)
- No filtros adicionales (por estado, área, fecha)
- No shadcn/ui Select (se usa native por consistencia)
- No tests del page component (no hay infraestructura de testing de componentes montados)

### Scope Decide
- **"Copiar a Excel"**: ¿debe copiar SOLO los resultados filtrados o TODOS los resultados? La decisión afecta a `copiarResultados()`.

## Approach

1. Agregar estado `const [respFilter, setRespFilter] = useState("")` en el componente
2. Extraer responsables únicos con `useMemo`:
   ```tsx
   const responsables = useMemo(() => {
     if (!results) return [];
     const set = new Set(results.map((r) => r.responsable || "—"));
     return Array.from(set).sort();
   }, [results]);
   ```
3. Filtrar resultados antes del render:
   ```tsx
   const filteredResults = useMemo(() => {
     if (!respFilter || !results) return results;
     return results.filter((r) => r.responsable === respFilter);
   }, [results, respFilter]);
   ```
4. Insertar `<select>` entre el header del card y la tabla (después del contador de facturas, antes del overflow-x-auto)
5. "Copiar a Excel" usará `filteredResults` si la decisión es copiar filtrados, o `results` si se decide copiar todos
6. Todas las referencias a `results` en el render de la tabla pasan a usar `filteredResults`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modified | +~40 líneas: estado, useMemo, select, filtered logic |
| `frontend/src/pages/abiertas-urgencias/utils.ts` | Possibly modified | copiarResultados si se decide copiar solo filtrados |
| `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts` | Possibly extended | Test para copiarResultados con subset |

## Capabilities

### New Capabilities
- `filtro-responsables`: Filtro dinámico por responsable en la tabla de Abiertas Urgencias. Las opciones se generan automáticamente de los resultados, sin configuración manual.

### Modified Capabilities
None

## Tradeoffs

| Opción | Pro | Contra |
|--------|-----|--------|
| Native `<select>` | Consistente con control-novedades, 0 dependencias, 0 import nuevo | Menos personalizable que shadcn Select |
| Copiar filtrados | El usuario copia solo lo que ve, UX predecible | No puede copiar todo sin limpiar filtro |
| Copiar todos | Siempre copia el dataset completo | Inconsistente con lo que ve en pantalla |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Responsable "Sin Egreso" / "—" se filtran mal | Low | Incluirlos explícitamente en el Set, el `useMemo` usa `|| "—"` |
| Resultados vacíos tras filtrar y se muestra tabla sin filas | Low | El header de resultados muestra `filteredResults.length` en vez de `results.length` |
| useEffect / useMemo no se actualizan al reprocesar | Low | `results` cambia por completo al reprocesar → nuevo Set, nuevo filtro |

## Rollback Plan

Revertir el commit. Es código puramente frontend: eliminar el state, los useMemo, el select, y restaurar `results.map(...)` en vez de `filteredResults.map(...)`.

## Dependencies

None

## Success Criteria

- [ ] Al cargar resultados, el `<select>` muestra "Todos" + cada responsable único presente en los datos
- [ ] Al seleccionar un responsable, la tabla muestra solo las filas de ese responsable
- [ ] Al seleccionar "Todos", se muestran todas las filas
- [ ] El contador de resultados se actualiza reflejando el filtro activo
- [ ] "Copiar a Excel" se comporta según la decisión tomada (filtrados vs todos)
- [ ] El dropdown incluye valores como "Sin Egreso", "—", etc. si existen en los datos
- [ ] El estilo del `<select>` es consistente con control-novedades
