# Proposal: Unificar base de procedimientos

## Intent

Eliminar la tabla PostgreSQL `procedimientos` (psycopg2 directo) como fuente redundante y unificar toda lectura de procedimientos/tarifas hacia la cadena SQLAlchemy (`eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`). Hoy existen DOS fuentes desconectadas con riesgo de inconsistencia y código muerto en endpoints CRUD.

## Scope

### In Scope
- Crear vista SQL `v_procedimientos` que una la cadena y presente estructura plana compatible
- Reescribir `app/services/procedimientos_db.py` → consultar la vista (misma interfaz, mismo contrato)
- Eliminar `app/services/procedimientos_crud.py` (endpoints POST/PUT/DELETE sin uso)
- Reducir `app/routes/procedimientos.py` a solo GET
- Migrar `app/services/verificar_codigos_urgencias.py` → SQLAlchemy chain
- Eliminar funciones muertas de `frontend/src/lib/api-catalogo.ts`
- Nueva migration SQL para la vista

### Out of Scope
- Eliminar la tabla `procedimientos` de PostgreSQL (requiere reconciliación previa)
- Modificar el pipeline `/procesar` (ya usa la cadena correctamente)
- Modificar la UI de Catálogos (ya usa la cadena)
- `data/create_db.py` y `data/procedimientos.db` (SQLite legacy)

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- None — mismo contrato GET, misma funcionalidad de verificación. Refactor de capa de datos solamente.

## Approach

**Vista SQL como capa de compatibilidad**, Approach A del explore:

1. **Migration SQL**: Crear `v_procedimientos` con JOIN de las 5 tablas, proyectando columnas equivalentes: `id, eps, codigo_cups, descripcion, tarifa, created_at, updated_at`
2. **Rewrite reads**: `procedimientos_db.py` mantiene misma interfaz pero consulta la vista vía psycopg2 (misma conexión, distintos queries)
3. **Eliminar writes**: Borrar `procedimientos_crud.py` y rutas POST/PUT/DELETE — nadie las consume
4. **Migrar script**: `verificar_codigos_urgencias.py` → query SQLAlchemy sobre `eps_contratado + procedimiento + notas_tecnicas`
5. **Limpiar frontend**: Remover `fetchProcPg`, `createProcPg`, `updateProcPg`, `deleteProcPg`, `fetchEpsDisponibles`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/procedimientos_db.py` | Modified | Reescribir queries hacia vista |
| `app/services/procedimientos_crud.py` | Removed | Código muerto |
| `app/routes/procedimientos.py` | Modified | Solo GET; quitar POST/PUT/DELETE |
| `app/services/verificar_codigos_urgencias.py` | Modified | psycopg2 → SQLAlchemy |
| `frontend/src/lib/api-catalogo.ts` | Modified | Eliminar 5 funciones muertas |
| `migrations/` | New | Migration SQL para `v_procedimientos` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Vista devuelve duplicados (mismo cups en múltiples notas_hoja) | Med | `SELECT DISTINCT ON (eps, codigo_cups)` en la vista; tests de integración |
| `verificar_codigos_urgencias.py` usa EPS por nombre, cadena usa `cod_contrato` | Med | Mapear "EMSSANAR_CAPITA" → `cod_contrato` correspondiente |
| Caller externo depende de endpoints POST/PUT/DELETE | Baja | Si aparece, reconectar vía API de catálogos existente |
| Timestamps nulos rompen consumidores | Baja | GET actual solo expone los campos; ningún consumer los parsea como date |

## Rollback Plan

1. Revertir migration (DROP VIEW v_procedimientos)
2. Restaurar `procedimientos_db.py`, `procedimientos_crud.py`, `procedimientos.py` desde git
3. Restaurar `verificar_codigos_urgencias.py` desde git
4. Restaurar `api-catalogo.ts` desde git

## Dependencies

- Migration tooling existente (SQLAlchemy + alembic-style SQL en `migrations/`)
- `psycopg2` connection config (`DB_CONFIG.psycopg2_dsn`) — se mantiene para queries a la vista

## Success Criteria

- [ ] `GET /procedimientos` responde con mismos datos que antes (misma interfaz)
- [ ] `GET /procedimientos/eps` lista EPS disponibles
- [ ] `GET /procedimientos/<eps>/<codigo>` busca correctamente
- [ ] `POST/PUT/DELETE /procedimientos` retornan 410 Gone
- [ ] `verificar_codigos_urgencias.py` funciona con el mismo Excel de prueba
- [ ] `api-catalogo.ts` compila sin errores tras eliminar funciones muertas
- [ ] Tests existentes pasan (si los hay para estos módulos)
