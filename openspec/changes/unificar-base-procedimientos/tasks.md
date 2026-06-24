# Tasks: Unificar base de procedimientos

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (25) → PR 2 (350) → PR 3 (124) |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Vista SQL + rewrite `procedimientos_db.py` | PR 1 | ~25 lines. Safe foundation, idempotent migration. |
| 2 | Eliminar writes + código muerto | PR 2 | ~350 lines (227 deletions). Depends on PR 1 view existing. |
| 3 | Script urgencias + limpiar frontend | PR 3 | ~124 lines. Independent from PR 2, depends on PR 1. |

## Batch 1: Migration + Read Rewrite

- [x] 1.1 Crear `migrations/003_create_v_procedimientos.sql` con `CREATE OR REPLACE VIEW v_procedimientos AS` (DDL del design §Query SQL). Verificar: ejecutar migration y consultar `SELECT COUNT(*) FROM v_procedimientos`.
- [x] 1.2 Modificar `app/services/procedimientos_db.py`: cambiar `FROM procedimientos` → `FROM v_procedimientos` en `get_procedimiento()` (línea 49), `get_all_by_codigo()` (línea 86), `get_all_by_eps()` (línea 122), `get_eps_disponibles()` (línea 150). Verificar: `curl GET /procedimientos?eps=EMSSANAR&all=true` retorna misma estructura JSON.

## Batch 2: Eliminar Código Muerto

- [x] 2.1 Eliminar `app/services/procedimientos_crud.py` completo (0 callers externos; verificado en proposal §Risks). Verificar: la app sigue arrancando sin `ImportError`.
- [x] 2.2 Modificar `app/routes/procedimientos.py`: eliminar imports de `procedimientos_crud` (líneas 14-19) y handlers POST (líneas 129-177), PUT (líneas 179-213), DELETE (líneas 216-234). Agregar 3 handlers `410 Gone` con mensaje `"Este endpoint ya no está disponible"`. Verificar: `curl -X POST /procedimientos` → `{"status":"error","errors":["Este endpoint ya no está disponible"]}` con 410.

## Batch 3: Migrar Script + Limpiar Frontend

- [x] 3.1 Modificar `app/services/verificar_codigos_urgencias.py`: reemplazar `from app.services.procedimientos_db import get_procedimiento` por import SQLAlchemy (`SessionLocal` de `app.database`, modelos `EpsContratado`, `Procedimiento`, `NotasTecnicas`, `EpsNota`, `NotaHoja`). Agregar `EPS_NAME_TO_COD_CONTRATO = {"EMSSANAR_CAPITA": "ESS118"}`. Reescribir loop de verificación con query `session.query(Procedimiento).join(...).filter(EpsContratado.cod_contrato == codigo).first()`. Verificar: ejecutar script con Excel de prueba → mismos `codigos_no_encontrados` y `codigos_encontrados`.
- [x] 3.2 Modificar `frontend/src/lib/api-catalogo.ts`: eliminar interface `ProcedimientoPg` (líneas 25-31) y funciones `fetchProcPg` (114-116), `fetchEpsDisponibles` (119-122), `createProcPg` (159-166), `updateProcPg` (195-200), `deleteProcPg` (203-205). Verificar: `cd frontend && npx tsc --noEmit` sin errores.
- [x] 3.3 Modificar `frontend/src/pages/catalogo/__tests__/api-catalogo.test.ts`: eliminar imports de `fetchProcPg`, `fetchEpsDisponibles`, `createProcPg`, `updateProcPg`, `deleteProcPg` (líneas 5-6, 14-16) y bloques `describe` de las 5 funciones (líneas 78-96, 172-192, 223-234, 254-260). Verificar: `cd frontend && npx vitest run api-catalogo` — tests restantes pasan.
