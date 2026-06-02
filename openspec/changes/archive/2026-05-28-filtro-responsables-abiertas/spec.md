# Filtro Responsables — Specification

## Purpose

Permitir filtrar la tabla de resultados de Abiertas Urgencias por responsable (facturador de turno) mediante un `<select>` nativo. Es puramente frontend: sin cambios en backend, APIs ni dependencias nuevas. Las opciones se extraen dinámicamente de los resultados actuales.

---

## Requirements

### R1: Selector Dinámico

The system MUST render a native `<select>` above the results table with all unique responsables from the current `results` array.

| # | Scenario | GIVEN | WHEN | THEN |
|---|----------|-------|------|------|
| 1.1 | Múltiples responsables | results tiene registros con "Ana", "Luis" | componente renderiza | `<select>` aparece con opciones "Todos", "Ana", "Luis" |
| 1.2 | Sin resultados | results = null o [] | componente renderiza | selector SHOULD estar oculto o deshabilitado |
| 1.3 | Único responsable | solo registros de "Ana" | componente renderiza | selector con "Todos" y "Ana" |

### R2: Filtro por Selección

The system MUST display only records whose `responsable` matches the selected option.

| # | Scenario | GIVEN | WHEN | THEN |
|---|----------|-------|------|------|
| 2.1 | Seleccionar | 10 regs, 3 responsables | usuario elige "Ana" | tabla: solo responsable === "Ana" |
| 2.2 | Volver a Todos | filtro = "Ana" activo | usuario elige "Todos" | tabla: todos los registros |
| 2.3 | Cambios sucesivos | filtro = "Ana" | usuario cambia "Luis" → "Carlos" | tabla refleja cada cambio |

### R3: Valores Atípicos

The system MUST include non-standard values as distinct filterable options.

| # | Scenario | GIVEN | WHEN | THEN |
|---|----------|-------|------|------|
| 3.1 | Especiales | registros con "Sin Egreso", "—" | dropdown se popula | esos valores son opciones |
| 3.2 | Null/undefined | responsable es null | extrayendo valores | se normaliza a "—" |

### R4: Opciones Únicas y Ordenadas

The system MUST deduplicate and sort responsables alphabetically.

| # | Scenario | GIVEN | WHEN | THEN |
|---|----------|-------|------|------|
| 4.1 | Deduplicación | 15 regs, 3 únicos | dropdown se popula | cada responsable una vez |
| 4.2 | Orden A-Z | "Luis", "Ana", "Carlos" | dropdown renderiza | orden: "Ana", "Carlos", "Luis" |

### R5: Copiar Solo Filtrados

On "Copiar a Excel", the system MUST copy ONLY the currently visible records.

| # | Scenario | GIVEN | WHEN | THEN |
|---|----------|-------|------|------|
| 5.1 | Filtro activo | filtro = "Ana", 3 visibles de 15 | usuario click "Copiar a Excel" | solo los 3 registros se copian |
| 5.2 | Sin filtro | filtro = "Todos", 15 visibles | usuario click "Copiar a Excel" | los 15 registros se copian |

### R6: Reactivo a Cambios

The selector MUST recalculate when `results` changes (reprocess, upload).

| # | Scenario | GIVEN | WHEN | THEN |
|---|----------|-------|------|------|
| 6.1 | Nuevos datos | selector: ["Todos", "Ana"] | nuevos results con "Luis", "Carlos" | selector actualizado |
| 6.2 | Reset si no existe | filtro = "Luis" | results sin "Luis" | filtro SHOULD reset a "Todos" |

### R7: Consistencia Visual

The `<select>` MUST use Tailwind classes matching control-novedades: `h-9 rounded-md border border-input bg-background px-3 text-sm`.

| # | Scenario | GIVEN | WHEN | THEN |
|---|----------|-------|------|------|
| 7.1 | Estilo | componente renderiza | inspeccionar clases del `<select>` | incluye todas las clases |

---

## Acceptance Criteria

- [ ] Selector aparece arriba de la tabla con todos los responsables únicos
- [ ] Opciones únicas, ordenadas alfabéticamente
- [ ] "Todos" es la opción por defecto
- [ ] Al seleccionar un responsable, la tabla muestra solo sus registros
- [ ] "Copiar a Excel" copia los registros visibles filtrados
- [ ] Valores atípicos ("Sin Egreso", "—") aparecen como opciones
- [ ] Al reprocesar datos, el selector se actualiza
- [ ] Visualmente consistente con control-novedades
