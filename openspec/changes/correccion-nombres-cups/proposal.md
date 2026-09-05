# Proposal: Corrección de nombres de procedimientos (CUPS)

## Intent

Los nombres en `procedimiento.procedimiento` no corresponden a los CUPS reales (325 registros). Las notas técnicas referencian los CUPS correctos vía FK, pero el campo legible tiene datos incorrectos.

## Scope

### In Scope
- Script standalone `scripts/correccion_nombres_cups.py` (~100 líneas)
- Backup CSV de `procedimiento` antes de escribir (timestamp en nombre)
- Actualizar `procedimiento.procedimiento` donde CUPS coincida y nombre difiera
- Logging estructurado: totales, actualizados, saltados, errores, duración

### Out of Scope
- Endpoints REST, UI/React, modelo de datos, migraciones Alembic — NO se tocan
- Columna `tariff` del Excel — no se usa
- Validación de relaciones — las FKs no cambian (mismos IDs)

## Capabilities

### New Capabilities
None — corrección única, no introduce capacidades nuevas.

### Modified Capabilities
None — no cambia comportamiento del sistema.

## Approach

Script standalone que:
1. Lee Excel con openpyxl, construye `dict[cups → procedimiento]`, ignora filas con `#NAME?`
2. Valida uniqueness de CUPS en Excel (logea y skipea duplicados)
3. Backup: exporta `procedimiento` a CSV en `backups/` con timestamp
4. Query todos los `Procedimiento` (SQLAlchemy)
5. Transacción: itera DB records, llama `procedimiento_crud.update()` donde nombre difiera
6. Commit si todo OK; rollback explícito en cualquier error
7. Reporte final: `"Actualizados: 325 | Saltados: X | Errores: 0 | Duración: Ns"`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `scripts/correccion_nombres_cups.py` | New | Script standalone de una ejecución |
| `app/services/procedimiento_crud.py` | Used | `update()` existente, sin modificar |
| `data/import/IMPORT PROCEDIMIENTO CORRECCION.xlsx` | Read-only | Fuente de datos |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CUPS duplicados en Excel (mismo cups, distinto nombre) | Low | Validar uniqueness al cargar; loggear y skipear |
| Celdas `#NAME?` (2 detectadas) | Low | Ignorar filas con error; loggear warning |
| Error DB a mitad de transacción | Low | Transacción con commit/rollback; backup previo |
| Cable cortado/panic antes de backup | Low | Backups previos existen si se re-ejecuta |

## Rollback Plan

1. **Automático**: backup CSV de `procedimiento` en `backups/procedimiento_YYYYMMDD_HHMMSS.csv`
2. **Manual**: `\copy procedimiento FROM 'backup.csv' DELIMITER ',' CSV HEADER;` en psql
3. **Transaccional**: si el script falla, rollback automático — DB queda intacta

## Dependencies

- openpyxl, SQLAlchemy, psycopg2 (ya instalados)
- `data/import/IMPORT PROCEDIMIENTO CORRECCION.xlsx` presente
- Conexión DB configurada en entorno

## Success Criteria

- [ ] Script ejecutado sin errores
- [ ] `# actualizados = 325` (o cifra reportada en logs)
- [ ] Backup CSV creado con timestamp en `backups/`
- [ ] Ninguna FK afectada — notas_tecnicas sigue apuntando a mismos IDs
