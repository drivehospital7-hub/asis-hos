# Design: Unificar base de procedimientos

## Technical Approach

Vista SQL `v_procedimientos` como capa de compatibilidad que aplana la cadena de 5 tablas (`eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`) a la estructura plana que espera `procedimientos_db.py`. El servicio read mantiene la misma interfaz pública pero consulta la vista vía psycopg2. El script `verificar_codigos_urgencias.py` migra a SQLAlchemy directo contra la cadena. Los endpoints de escritura se eliminan (410 Gone).

## Architecture Decisions

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| **Tarifa en vista con duplicados** | `tariff DESC` (máxima) | `nt.id DESC` (más reciente) | **A** | Conservador para verificación: si el Excel trae tarifa menor que la máxima contratada, se detecta. La más reciente podría ocultar una tarifa mayor contratada antes. |
| **verificar_codigos_urgencias** usa vista o SQLAlchemy | Vista v_procedimientos | SQLAlchemy directo contra la cadena | **B** | El script busca por `cod_contrato` ("ESS118"), no por `eps` nombre. SQLAlchemy directo permite `filter(EpsContratado.cod_contrato == ...)`. La vista solo expone `eps` (nombre), no `cod_contrato`. |
| **Mapeo "EMSSANAR_CAPITA"** | Fuzzy match `eps_contratado.eps ILIKE` | Hardcoded dict `{"EMSSANAR_CAPITA": "ESS118"}` | **B** | Explícito y auditable. Fuzzy match es frágil ante variaciones de nombres. Si aparecen más entidades, se agregan al dict. |
| **procedimientos_db.py motor** | Psycopg2 (misma conexión) | SQLAlchemy | **A** | Menor superficie de cambio. La vista `v_procedimientos` es una tabla lógica PostgreSQL — psycopg2 la consulta igual que cualquier tabla. No requiere refactor de `_get_connection()`. |

## Query SQL: `v_procedimientos`

```sql
CREATE OR REPLACE VIEW v_procedimientos AS
SELECT
    ROW_NUMBER() OVER (ORDER BY eps, codigo_cups) AS id,
    eps,
    codigo_cups,
    descripcion,
    tarifa,
    created_at,
    updated_at
FROM (
    SELECT DISTINCT ON (ec.eps, p.cups)
        ec.eps,
        p.cups AS codigo_cups,
        p.procedimiento AS descripcion,
        nt.tariff AS tarifa,
        CAST(NULL AS TIMESTAMPTZ) AS created_at,
        CAST(NULL AS TIMESTAMPTZ) AS updated_at
    FROM eps_contratado ec
    JOIN eps_nota en ON en.id_eps_contratado = ec.id
    JOIN nota_hoja nh ON nh.id = en.id_nota_hoja
    JOIN notas_tecnicas nt ON nt.id_nota_hoja = nh.id
    JOIN procedimiento p ON p.id = nt.id_procedimiento
    ORDER BY ec.eps, p.cups, nt.tariff DESC
) sub;
```

- `DISTINCT ON (ec.eps, p.cups)` con `ORDER BY ... tariff DESC` → 1 fila por (eps, cups), tarifa más alta
- Subquery exterior asigna `ROW_NUMBER()` secuencial como `id` (INTEGER, convertido a `str` en el servicio para mantener compatibilidad con UUID anterior)
- `created_at` / `updated_at` son NULL (la cadena no tiene timestamps; los consumidores no los parsean)

## Sequence Diagrams

### `get_procedimiento(eps, codigo_cups)`

```
Caller ──→ procedimientos_db.get_procedimiento("EMSSANAR", "890201")
               │
               ├─ _get_connection() → psycopg2.connect(**DB_CONFIG.psycopg2_dsn)
               ├─ cursor.execute("SELECT ... FROM v_procedimientos WHERE eps=%s AND codigo_cups=%s", ...)
               ├─ row = cursor.fetchone()
               ├─ cursor.close() / conn.close()
               │
               └─→ Procedimiento(id="42", eps="EMSSANAR", codigo_cups="890201", ...)
                   o None si no existe
```

### `get_eps_disponibles()`

```
Caller ──→ procedimientos_db.get_eps_disponibles()
               │
               ├─ cursor.execute("SELECT DISTINCT eps FROM v_procedimientos ORDER BY eps")
               └─→ ["ASMET_SALUD", "EMSSANAR", "MALLAMAS"]
```

### `get_all_by_eps(eps)` / `get_all_by_codigo(codigo_cups)`

```
Caller ──→ get_all_by_eps("EMSSANAR")
               │
               ├─ cursor.execute("SELECT ... FROM v_procedimientos WHERE eps=%s ORDER BY codigo_cups", ...)
               └─→ List[Procedimiento]
```

### `verificar_tarifa(eps, codigo_cups, tarifa_excel)`

```
Caller ──→ verificar_tarifa("EMSSANAR", "890201", 45000.50)
               │
               ├─ proc = get_procedimiento("EMSSANAR", "890201")  # 1 query a la vista
               ├─ if not proc → (False, "no encontrado")
               ├─ if proc.tarifa is None → (True, "tarifa no definida")
               └─ diff = |proc.tarifa - 45000.50| ≤ tolerancia → (True/False, mensaje)
```

### `verificar_codigos_urgencias.py` (nuevo flujo SQLAlchemy)

```
Script ──→ verificar_excel(excel_path)
               │
               ├─ Lee Excel, extrae códigos únicos para ESS118
               ├─ SessionLocal()  ← app.database
               ├─ Para cada código:
               │    result = session.query(Procedimiento)
               │        .join(NotasTecnicas)
               │        .join(NotaHoja)
               │        .join(EpsNota)
               │        .join(EpsContratado)
               │        .filter(EpsContratado.cod_contrato == "ESS118")
               │        .filter(Procedimiento.cups == codigo)
               │        .first()
               │    └─→ encontrado / no encontrado
               └─ session.close()
```

## EPS Mapping Strategy

`verificar_codigos_urgencias.py` mantiene la constante `EPS_DB` pero reinterpretada:

```python
# Antes: string usado como eps en tabla procedimientos
EPS_DB = "EMSSANAR_CAPITA"

# Ahora: mapping explícito al cod_contrato de la cadena
EPS_NAME_TO_COD_CONTRATO = {
    "EMSSANAR_CAPITA": "ESS118",
}
```

La query SQLAlchemy usa `EpsContratado.cod_contrato` como clave de búsqueda. Si en el futuro otro script usa un nombre de EPS distinto, se agrega al dict.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `migrations/003_create_v_procedimientos.sql` | **Create** | `CREATE OR REPLACE VIEW v_procedimientos` |
| `app/services/procedimientos_db.py` | **Modify** | Cambiar queries `FROM procedimientos` → `FROM v_procedimientos`. `id` se castea `str(row["id"])`. Sin cambios en firma pública. |
| `app/services/procedimientos_crud.py` | **Delete** | Código muerto, 0 callers fuera del blueprint eliminado |
| `app/routes/procedimientos.py` | **Modify** | Eliminar POST/PUT/DELETE y sus imports de `procedimientos_crud`. Agregar handlers 410 Gone. Mantener GET + `/eps`. |
| `app/services/verificar_codigos_urgencias.py` | **Modify** | Reemplazar `from app.services.procedimientos_db import get_procedimiento` por query SQLAlchemy directa (models + SessionLocal). Agregar `EPS_NAME_TO_COD_CONTRATO`. |
| `frontend/src/lib/api-catalogo.ts` | **Modify** | Eliminar: `ProcedimientoPg` (interface), `fetchProcPg`, `fetchEpsDisponibles`, `createProcPg`, `updateProcPg`, `deleteProcPg` |
| `frontend/src/pages/catalogo/__tests__/api-catalogo.test.ts` | **Modify** | Eliminar: imports de las 5 funciones + 5 bloques `describe` correspondientes |

## Migration / Rollout

### Paso a paso

1. **Crear migration** `003_create_v_procedimientos.sql` con el DDL de la vista
2. **Ejecutar migration** `python run_migrations.py` → vista creada en PostgreSQL
3. **Modificar `procedimientos_db.py`**: queries apuntan a `v_procedimientos`; id → `str()`
4. **Modificar `routes/procedimientos.py`**: quitar POST/PUT/DELETE, agregar 410 handlers
5. **Eliminar `procedimientos_crud.py`**
6. **Modificar `verificar_codigos_urgencias.py`**: SQLAlchemy directo + mapping dict
7. **Modificar frontend**: eliminar 5 funciones + `ProcedimientoPg` interface + tests
8. **Verificar**: endpoints GET, script de urgencias, compilación TypeScript

### Rollback

```bash
# 1. Revertir vista
psql -c "DROP VIEW IF EXISTS v_procedimientos;"

# 2-6. Restaurar archivos desde git
git checkout -- app/services/procedimientos_db.py \
                app/services/procedimientos_crud.py \
                app/routes/procedimientos.py \
                app/services/verificar_codigos_urgencias.py \
                frontend/src/lib/api-catalogo.ts \
                frontend/src/pages/catalogo/__tests__/api-catalogo.test.ts

# 7. Eliminar migration
rm migrations/003_create_v_procedimientos.sql
```

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| DB | Vista `v_procedimientos` retorna datos correctos | `run_migrations.py` + query manual `SELECT COUNT(*)` |
| Service | `procedimientos_db.py` consulta la vista correctamente | Test manual con `python -m app.services.procedimientos_db` |
| HTTP | GET endpoints responden igual estructura JSON | `curl GET /procedimientos?eps=...&all=true` → comparar con respuesta anterior |
| HTTP | POST/PUT/DELETE retornan 410 | `curl -X POST` → `{"status":"error","errors":["Este endpoint ya no está disponible"]}` |
| Script | `verificar_codigos_urgencias.py` mismo resultado | Ejecutar con Excel de prueba, comparar `codigos_no_encontrados` y `codigos_encontrados` |
| Frontend | TypeScript compila sin errores | `cd frontend && npx tsc --noEmit` |
| Frontend | Tests restantes pasan | `cd frontend && npx vitest run api-catalogo` |

## Open Questions

- [ ] Confirmar que `cod_contrato` "ESS118" corresponde efectivamente a "EMSSANAR_CAPITA" en la BD de producción. Si difiere, ajustar `EPS_NAME_TO_COD_CONTRATO`.
- [ ] Validar que ningún otro script o módulo importa `procedimientos_crud` (grep confirma 0 callers; verificar en prod).
