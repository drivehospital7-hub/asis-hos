# Proposal: Reglas multi-dominio

## Intent

Una regla debe poder aplicarse a más de un dominio explícito (p. ej. `urgencias` +
`hospitalización` sin incluir `odontología`). Hoy `reglas.dominio` es un único
`String(50)` por fila y el único "multi-dominio" existente es el comodín
`'transversal'` (= todos los dominios), implementado como cláusulas OR repetidas
en 4 puntos del motor. Duplicar reglas por dominio (vía `duplicate_rule`)
fragmenta el mantenimiento: N copias que divergen.

Decisión de producto ya tomada: lista explícita de dominios por regla +
`'transversal'` se mantiene como comodín "aplica en todos".

## Scope

### In Scope
- Nuevo modelo/tabla `regla_dominios(regla_id, dominio)` como fuente de verdad de
  alcance; migración `023_*` con backfill desde `reglas.dominio`.
- Motor: `rule_resolver.resolve`, `domain_detection._load_selected_rules`,
  `engine._load_rule_by_name` (incl. orden exact-first) matchean contra la tabla
  puente + comodín transversal.
- CRUD (`rule_service` + `reglas_api`): aceptar/validar `dominios: string[]`,
  mantener compat con `dominio: string` legacy.
- UI admin-reglas: crear/editar con multi-check, badges múltiples, filtros por
  dominio (match si el dominio filtrado ∈ lista de la regla).
- Vocabulario canónico centralizado en `app/constants/` (fin del hardcode
  esparcido entre `DOMINIOS` del frontend y seeds).
- Tests: migración/backfill, resolución por dominio (1, N, transversal,
  solapados), CRUD con validación, UI.

### Out of Scope
- Cambiar `evidencias.dominio` (snapshot inmutable del dominio evaluado; sigue
  `String(50)` single-value).
- Cambiar `catalogos.dominio` (vocabulario separado y libre).
- Borrar la columna legacy `reglas.dominio` (queda como espejo solo-lectura
  para compatibilidad de evidencia histórica y rollback).
- Reglas "transversal con excepciones" (rechazado en la decisión de producto).

### Capabilities
- **New** `reglas-multi-dominio`: alcance N-dominios por regla con validación
  de vocabulario y preservación de la semántica transversal-matches-all.

## Approach

### Representación: tabla puente (no JSONB)

`regla_dominios(regla_id FK → reglas.id ON DELETE CASCADE, dominio String(50),
PRIMARY KEY (regla_id, dominio))` + índice `(dominio, regla_id)`.

Rationale: el proyecto corre PostgreSQL en prod y SQLite en tests. Una lista
JSONB exigiría operadores no portables (`?` en PG vs `json_each` en SQLite);
la tabla puente usa `EXISTS` portable e indexable en ambos. Además no toca el
`UniqueConstraint(nombre, version)` (que ya excluye dominio y hoy colisionaría
con filas multi-dominio) ni invalida datos históricos.

### Migración 023 (aditiva, formato `NNN_*.sql`, vía `run_migrations.py`)

1. `CREATE TABLE regla_dominios (...)`.
2. Backfill: `INSERT INTO regla_dominios SELECT id, dominio FROM reglas`
   (cubre el 100% de filas existentes; `dominio` es NOT NULL).
3. Índices nuevos. La columna `reglas.dominio` y el índice composite viejo se
   conservan (rollback seguro, lectores legacy intactos).

### Motor (4 puntos, mismo shape OR que hoy, contra la puente)

```python
# antes
filter((Regla.dominio == domain) | (Regla.dominio == 'transversal'))
# después
filter(exists_regla_dominio(Regla.id, [domain, ENGINE_DOMAIN_TRANSVERSAL]))
```

Helper compartido (p. ej. en `rule_resolver.py` o `models.py`) para no repetir
el `EXISTS`: `rule_matches_domain(regla_id_expr, domain)`. Los literales
`'transversal'` sueltos se reemplazan por `ENGINE_DOMAIN_TRANSVERSAL`
(`app/constants/base.py:222`). `_load_rule_by_name` conserva exact-first con
dos EXISTS ordenados (exacto 0, transversal 1) + `version DESC`.
Filas sin entradas en la puente (defensa, no debería ocurrir post-backfill):
fallback a la semántica legacy single-column.

### Backend CRUD + validación (nueva)

- `REGLA_DOMINIOS_VALIDOS` en `app/constants/base.py`: los 8 valores
  observados (`urgencias`, `hospitalizacion`, `odontologia`, `equipos_basicos`,
  `transversal`, `farmacia`, `intramural`, `ambulatoria`).
- `create_rule`/`update_rule`: aceptan `dominios: [...]`, validan no-vacío +
  vocabulario; escriben puente + espejo legacy (`dominio` = primer valor
  ordenado, solo para lectores viejos). Sin `dominios` explícito: `dominio`
  single actual como lista de 1 (compat total con callers actuales).
- `to_dict` suma `dominios: [...]`, conserva `dominio`.
- `duplicate_rule`/`create_version` copian la lista. `list_rules(dominio=X)`:
  match si X ∈ lista (incluye transversales, consistente con el motor).

### Frontend admin-reglas

- `api-reglas.ts`: `Regla.dominios: string[]` (+ `dominio` legacy).
- `DOMINIOS` pasa a importarse de una fuente única compartida con el backend
  en espíritu (mismo orden/contenido que `REGLA_DOMINIOS_VALIDOS`).
- Crear/editar: multi-check en vez de single `<select>`; badges apilados;
  filtros principal y evidencias con semántica "∈ lista".

## Decisions Needed

1. **Espejo legacy**: `reglas.dominio` = primer dominio ordenado al escribir
   (recomendado) vs congelar el valor pre-migración. Recomiendo espejo vivo:
   mantiene coherencia para lectores viejos sin costo.
2. **Vocabulario**: confirmar los 8 valores (`extramural`/`unificada`/
   `auditoria` son áreas, no dominios de regla — quedan fuera).
3. **Filtro de listado**: `?dominio=X` incluye transversales (recomendado,
   consistente con el motor) vs solo match exacto.

## Effort Estimate

**Medio-alto.** Estimación honesta: supera el budget de revisión de 400 líneas
(migración + modelo + servicio + 4 puntos del motor + rutas + UI + tests), por
lo que bajo la estrategia `single-pr` requerirá `size:exception` explícito
antes del apply. Archivos nuevos: 1 migración, ~1 modelo (en `models.py`),
tests (backend + frontend). Modificados: `models.py`, `rule_service.py`,
`reglas_api.py`, `rule_resolver.py`, `domain_detection.py`, `engine.py`,
`api-reglas.ts`, `page.tsx`, `constants/base.py`.

## Rollback Plan

- Migración aditiva: rollback = `DROP TABLE regla_dominios` (script
  `023_*_rollback.sql` por convención) + revert de código; `reglas.dominio`
  nunca se toca, así que el motor legacy sigue funcionando.
- Sin pérdida de datos: backfill es INSERT-only; evidencias intactas.

## Risks

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Sin validación backend hoy: datos inválidos existen | Media | Validar en escritura + test que audita valores fuera de vocabulario |
| Dedup por nombre (`seen` set) con listas solapadas | Baja | Semántica "una evaluación por (run de dominio, nombre)" no cambia: 1 fila = 1 regla |
| Reportes mezclan evidencia pre/post migración | Baja | Evidencia sigue snapshot single del dominio evaluado; sin cambio de formato |
| Exceder budget de revisión | Alta | Estrategia `single-pr` → pedir `size:exception` antes del apply |

## Success Criteria

- [ ] Migración 023 aplica en PG y su SQL es portable a SQLite (o testeada
      como SQL-text según precedente 022)
- [ ] Regla con `dominios=[urgencias, hospitalizacion]` dispara en ambos
      dominios y en ningún otro; transversal sigue matcheando todo
- [ ] CRUD valida vocabulario y rechaza listas vacías/inválidas
- [ ] UI crear/editar/filtrar opera con múltiples dominios sin regression
      single-dominio
- [ ] Suite completa verde (`pytest` + `vitest` admin-reglas)
