# Tasks: Reset DB + Reimportación Progresiva

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~165 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation + Core + Verification | PR 1 | Single PR (<400 lines), no split needed |

## Phase 1: Foundation — Migración DDL

- [x] 1.1 Crear `migrations/002_create_procedimientos.sql` con CREATE TABLE (UUID PK, eps, codigo_cups, descripcion, tarifa, timestamps) + índice compuesto `idx_procedimientos_eps_codigo`
- [x] 1.2 Verificar que la migración es idempotente: `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`

## Phase 2: Core — Script Reset DB

- [x] 2.1 Crear `scripts/reset_db.py`: conexión psycopg2 vía `DB_CONFIG.psycopg2_dsn` con `autocommit=True`
- [x] 2.2 Implementar `--force` flag (argparse) y confirmación stdin `"s/N"` cuando no hay `--force`
- [x] 2.3 Implementar logging por paso con timestamp ISO8601: `[DROP] tabla`, `[CREATE] tabla`, `[SEED]`, `[DONE]`
- [x] 2.4 Implementar DROP TABLE IF EXISTS ... CASCADE en orden inverso de FKs
- [x] 2.5 Ejecutar `Base.metadata.create_all()` para las 7 tablas SQLAlchemy
- [x] 2.6 Ejecutar `run_migrations()` para correr migraciones SQL (001 + 002)
- [x] 2.7 Ejecutar seed de usuarios vía `crear_usuarios.py` (import directo)
- [x] 2.8 Manejo de errores: abortar con exit code != 0 si un DROP/CREATE falla

## Phase 3: Verification

- [x] 3.1 Ejecutar `python scripts/reset_db.py --force` contra DB de prueba
- [x] 3.2 Verificar que las 8 tablas existen (8/8: users, user_areas, eps_contratado, procedimiento, nota_hoja, notas_tecnicas, eps_nota, procedimientos)
- [x] 3.3 Verificar idempotencia: dos resets seguidos — idéntico resultado
- [x] 3.4 Verificar seed: admin, odonto_user, urgencias_user creados correctamente

## Implementation Order

Foundation → Core → Verification. Cada fase depende estrictamente de la anterior (la migración DDL debe existir antes de que `reset_db.py` la ejecute). Fase 1 y 2 pueden implementarse en una sola sesión.
