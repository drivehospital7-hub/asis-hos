# Design: Reset DB + Reimportación Progresiva

## Technical Approach

Script standalone `scripts/reset_db.py` que se conecta directo a PostgreSQL vía psycopg2 (sin Flask), dropea las 8 tablas en orden inverso de FKs, recrea ambos schemas (SQLAlchemy + manual), ejecuta migraciones y seed. La reimportación guiada es CLI interactiva que secuencia las cargas reusando endpoints `/api/import/` existentes, y usando psycopg2 directo para la tabla `procedimientos` (fuera de SQLAlchemy).

## Architecture Decisions

### Decision 1: ¿Psycopg2 directo o SQLAlchemy text() para el reset?

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| psycopg2 directo (reusando `DB_CONFIG.psycopg2_dsn`) | Misma conexión que `procedimientos_crud.py` y `run_migrations.py`. Sin dependencia de SQLAlchemy. | ✅ |
| SQLAlchemy `text()` + `engine.connect()` | Requiere tener `_get_engine()` activo. No puede dropear tablas que SQLAlchemy no conoce (e.g. `procedimientos`). | ❌ |

**Rationale**: El script debe dropear la tabla `procedimientos` (psycopg2, fuera de SQLAlchemy). Usar psycopg2 evita mezclar concerns y es el mismo patrón que `run_migrations.py`. Además, el drop requiere `autocommit = True` (DDL), que psycopg2 maneja trivialmente.

### Decision 2: ¿CLI interactivo o flags para el reset?

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| `--force` flag + confirmación sí/no en stdin | Mínimo: `scripts/reset_db.py` o `scripts/reset_db.py --force` | ✅ |
| CLI interactivo con menú completo | Más complejo, el reset es binario (se hace o no). | ❌ |

**Rationale**: El reset es una operación atómica — o se dropea todo o nada. La confirmación evita accidents. `--force` salta el prompt para CI/automation.

### Decision 3: ¿Script standalone o comando Flask?

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Script standalone (`python scripts/reset_db.py`) | Sin depender del servidor Flask. Se puede ejecutar mientras la app corre. | ✅ |
| Comando Flask (`flask db-reset`) | Requiere que la app esté configurada. Mayor acoplamiento. | ❌ |

**Rationale**: El reset debe poder ejecutarse sin que el servidor Flask esté corriendo (e.g. antes del primer deploy). Es un script de infraestructura, no una feature de la app. Mismo patrón que `crear_usuarios.py` y `run_migrations.py`.

### Decision 4: ¿Cómo manejar `procedimientos` (tabla psycopg2)?

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Extraer DDL a `migrations/002_create_procedimientos.sql` | Centraliza el schema. Documentado, versionado. | ✅ |
| Inline en `reset_db.py` | Más frágil, el DDL se pierde entre el código. | ❌ |

**Rationale**: La tabla `procedimientos` no tiene DDL en el repo. Crear `migrations/002_create_procedimientos.sql` la documenta y la migración existente `run_migrations.py` la ejecutará automáticamente. El reset_db.py solo debe llamar a `run_migrations()`.

## Data Flow

```
scripts/reset_db.py [--force]
    │
    ├─ 1. Conectar psycopg2 (autocommit=True)
    ├─ 2. DROP TABLE IF EXISTS ... CASCADE
    │    └─ orden: notas_tecnicas, eps_nota, eps_contratado,
    │       procedimiento, nota_hoja, user_areas, users, procedimientos
    ├─ 3. Base.metadata.create_all() → 7 tablas SQLAlchemy
    └─ 4. run_migrations() → 001_create_notas_tecnicas.sql + 002_create_procedimientos.sql
    └─ 5. Seed: crear_usuarios.py

Reimportación guiada (CLI):
    Paso 1: Seed de usuarios (automático, ya ejecutado)
    Paso 2: /api/import/eps          → eps_contratado.csv
    Paso 3: /api/import/procedimientos → procedimiento.csv (singular)
    Paso 4: /api/import/notas-hoja    → nota_hoja.csv
    Paso 5: INSERT directo psycopg2    → procedimientos.csv (plural)
    Paso 6: /api/import/notas-tecnicas → notas_tecnicas.csv
    Paso 7: /api/import/eps-nota      → eps_nota.csv
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `scripts/reset_db.py` | Create | Script standalone: drop → create → migrate → seed |
| `migrations/002_create_procedimientos.sql` | Create | DDL de `procedimientos` (UUID PK, eps, codigo_cups, descripcion, tarifa, created_at, updated_at) con índices |

## Interfaces / Contracts

```python
# scripts/reset_db.py — CLI
# Uso: python scripts/reset_db.py [--force]
# Sin --force: pide confirmación "¿Resetear DB? Esto destruye TODOS los datos. (s/N): "
# Con --force: ejecuta sin preguntar

# Logging: logging con timestamp ISO8601 por paso
#   2026-06-05 14:30:01 - Dropeando tabla: notas_tecnicas
#   2026-06-05 14:30:01 - OK
#   2026-06-05 14:30:02 - Creando tablas SQLAlchemy...
#   ...
```

### Procesos de reimportación

- **Tablas SQLAlchemy** (5 endpoints): se reusan tal cual — POST multipart con CSV
- **Tabla `procedimientos`** (psycopg2 sin endpoint): script helper inline en el CLI que parsea CSV y hace inserts vía `psycopg2` directo, reusando validación de `procedimientos_crud.py`
- **Seed**: `crear_usuarios.py` vía `subprocess.run()` o import directo (mismo pattern que `run_migrations.py`)

### Migración 002

```sql
CREATE TABLE IF NOT EXISTS procedimientos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    eps TEXT NOT NULL,
    codigo_cups TEXT NOT NULL,
    descripcion TEXT,
    tarifa NUMERIC(12,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_procedimientos_eps_codigo
    ON procedimientos(eps, codigo_cups);
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Integration | Reset completo | Ejecutar `reset_db.py --force`, verificar que tablas existen y están vacías |
| Integration | Idempotencia | Ejecutar reset dos veces seguidas — no debe fallar |
| Manual | Reimportación guiada | Ejecutar reset, luego cada paso de reimport con CSV de prueba |

## Migration / Rollout

No migration requerida — el cambio es puramente operativo. La migración `002_create_procedimientos.sql` es nueva y solo se ejecuta post-reset. Los datos existentes NO se migran; se dropean y reimportan.

Rollback: restaurar backup PostgreSQL externo (responsabilidad del operador).

## Open Questions

- [ ] El DDL exacto de `procedimientos` (UUID vs SERIAL, defaults) debe verificarse contra la DB actual — inferido del código pero no confirmado.
- [ ] El CLI de reimportación: ¿script separado (`scripts/reimport.py`) o integrado en `reset_db.py` como `--reimport`? Lo separamos para mantener SRP.
