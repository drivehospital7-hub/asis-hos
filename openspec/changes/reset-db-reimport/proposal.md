# Proposal: Reset DB + Reimportación Progresiva

## Intent

Proveer un script que resetea por completo la base de datos PostgreSQL (`asis_hos`) y una sesión guiada de reimportación que permite al usuario cargar progresivamente los archivos de datos, reutilizando los endpoints de import existentes.

Actualmente no existe forma de reiniciar la DB — solo `Base.metadata.create_all()` en `crear_usuarios.py`. Dos schemas paralelos (SQLAlchemy + psycopg2 directo) complican el reset manual.

## Scope

### In Scope
- `scripts/reset_db.py` — dropea todas las tablas (ambos schemas) y las recrea en orden con FKs
- Reutilización de los 5 endpoints `/api/import/` + seed de usuarios para reimportar
- Sesión guiada: el usuario sube archivos uno a uno, se importan en el orden correcto
- Migraciones SQL re-ejecutadas automáticamente post-reset

### Out of Scope
- Modificar modelos SQLAlchemy ni esquemas de datos
- Crear nuevos endpoints de import (se reusan los existentes)
- Modificar config de DB, conexiones, ni manejo de backups
- Soporte para archivos Excel en los endpoints de import

## Capabilities

<!-- This change adds no new capabilities nor modifies existing spec-level behavior.
     It's a pure operational utility (reset + guided reimport). -->
- **New Capabilities**: None
- **Modified Capabilities**: None

## Approach

**Fase 1 — Reset**: `scripts/reset_db.py` se conecta a PostgreSQL vía psycopg2 y ejecuta:
1. `DROP TABLE IF EXISTS ... CASCADE` para las 8 tablas (orden inverso a FKs)
2. `Base.metadata.create_all()` para las 7 tablas SQLAlchemy
3. DDL manual para `procedimientos` (plural) — CREATE TABLE vía psycopg2
4. Ejecuta migraciones SQL (`run_migrations.py` vía llamada directa)
5. Seed de usuarios (`crear_usuarios.py` vía subprocess o import)

**Fase 2 — Reimportación guiada**: CLI interactivo que guía al usuario paso a paso:
1. users (seed automático, no requiere archivo)
2. eps_contratado → endpoint `/api/import/eps`
3. procedimiento (singular) → endpoint `/api/import/procedimientos`
4. nota_hoja → endpoint `/api/import/notas-hoja`
5. procedimientos (plural) → psycopg2 directo
6. notas_tecnicas → endpoint `/api/import/notas-tecnicas`
7. eps_nota → endpoint `/api/import/eps-nota`

Cada paso espera que el usuario proporcione el archivo correspondiente; puede saltarse si no aplica.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `scripts/reset_db.py` | New | Script principal de reset |
| `app/services/procedimientos_db.py` | None used | Solo referencia para DDL de `procedimientos` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `procedimientos` (plural) no está en SQLAlchemy — su DDL debe mantenerse sincronizada | Medium | Extraer CREATE TABLE del código existente, documentar en reset_db.py |
| Reset es destructivo — no hay vuelta atrás | High | Backup de la DB ya existe externamente; el script confirma antes de ejecutar |
| Endpoints de import esperan CSV, el usuario puede tener Excel | Medium | El script guiado convierte Excel a CSV antes de enviar, o el usuario exporta manualmente |
| El seed de usuarios crea usuarios si no existen (idempotente) | Low | No hay riesgo — `crear_usuarios.py` ya usa `if not` checks |

## Rollback Plan

El backup de la DB ya existe externamente (responsabilidad del usuario). El script `reset_db.py` es un paso único sin reversa programática — después de dropear, solo hay reimport. Si algo falla durante la reimportación, se puede re-ejecutar el script de reset y empezar de nuevo.

## Dependencies

- PostgreSQL `asis_hos` accesible vía `DB_CONFIG`
- Servidor Flask ejecutándose con los endpoints `/api/import/` disponibles
- Archivos de datos del usuario en formato CSV (o convertibles)

## Success Criteria

- [ ] `scripts/reset_db.py` ejecutado sin errores, tablas creadas en orden (FKs satisfechas)
- [ ] Seed de usuarios ejecutado post-reset (admin + odonto_user + urgencias_user)
- [ ] Cada archivo provisto se importa correctamente vía su endpoint correspondiente
- [ ] Datos reimportados verificables: consultas a las tablas devuelven registros esperados
