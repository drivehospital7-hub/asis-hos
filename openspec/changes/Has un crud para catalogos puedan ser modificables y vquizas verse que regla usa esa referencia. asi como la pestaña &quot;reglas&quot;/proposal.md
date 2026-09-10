# Proposal: CRUD catálogos modificables + reglas que los referencian

## Intent

Hoy los catálogos JSONB (`catalogos`) solo se leen vía `GET /api/catalogos/<key>`. No hay forma de editarlos desde la UI ni de saber qué reglas dependen de cada uno. Esto obliga a modificarlos directo en DB y rompe reglas sin advertencia.

## Scope

### In Scope
- API CRUD completa para `catalogos` + endpoint de reglas referentes
- Página `admin-catalogos` con tabla, editor de valores, y vista de reglas vinculadas
- Validación de dependencias antes de delete
- Tests backend + frontend

### Out of Scope
- Migración de catálogos hardcodeados a la tabla (datos ya existen)
- Versionado de cambios en valores del catálogo
- Catálogos multi-dominio (se maneja con distintos keys)

## Capabilities

### New Capabilities
- `catalogos-crud`: CRUD completo sobre la tabla `catalogos` (JSONB) + consulta de reglas que referencian cada catálogo

### Modified Capabilities
None

## Approach

**API** (en `reglas_api.py`, mismo blueprint `/api`):

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/catalogos` | GET | Listar todos (key, descripción, dominio, value count) |
| `/api/catalogos` | POST | Crear nuevo catálogo |
| `/api/catalogos/<key>` | GET | Obtener valores (existe) |
| `/api/catalogos/<key>` | PUT | Reemplazar array JSONB |
| `/api/catalogos/<key>` | DELETE | Eliminar (valida dependencias primero) |
| `/api/catalogos/<key>/reglas` | GET | Reglas que usan `cat_in` con este key |

**DELETE** valida: query `condiciones WHERE operador='cat_in' AND valor_esperado=:key`. Si hay reglas activas → error 409 con lista de reglas. Si solo hay draft/retired → permitir con warning.

**Key inmutable** — POST define key, PUT no lo cambia. Para renombrar hay que crear nuevo y migrar reglas manualmente.

**Frontend** — nueva página `admin-catalogos` siguiendo el patrón `admin-reglas`:
- MPA entry: `frontend/src/pages/admin-catalogos/` con `index.html`, `main.tsx`, `page.tsx`
- Ruta Flask: `GET /admin/catalogos` → `react_shell.html` (mismo patrón que `reglas_admin.py`)
- Registro en `vite.config.ts` input array
- Componentes: tabla listado (key, descripción, dominio, preview valores, #reglas), modal editor de valores (tag input para strings), modal "Ver reglas" (tabla con regla_id, nombre, condición)

**JSONB editing UX** — tag input con shadcn/ui como base (editar strings), botón "+" para agregar, "×" para quitar. Para valores no-string (números), raw JSON editor en modal secundario. Esto cubre el caso actual donde todos los catálogos son arrays de strings.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/routes/reglas_api.py` | Modified | +5 endpoints catalogos CRUD + reglas refs |
| `app/routes/reglas_admin.py` | Modified | +ruta `/admin/catalogos` |
| `app/services/reglas/catalogo_service.py` | New | SRP: lógica CRUD + validación dependencias |
| `frontend/src/pages/admin-catalogos/page.tsx` | New | Componente React con shadcn/ui |
| `frontend/src/pages/admin-catalogos/main.tsx` | New | Entry point con AppLayout |
| `frontend/src/pages/admin-catalogos/index.html` | New | HTML shell |
| `frontend/src/lib/api-reglas.ts` | Modified | +fetchCatalogos, createCatalogo, etc. |
| `frontend/vite.config.ts` | Modified | +input entry admin-catalogos |
| `tests/routes/test_catalogos_api.py` | New | Tests CRUD + validación delete |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Delete catálogo usado por reglas activas rompe evaluación | Media | Validar dependencias antes de DELETE, error 409 con lista |
| Key inmutable — no se puede renombrar | Baja | Documentar en UI: key se define al crear y no se edita |
| JSONB array con tipos mixtos (string + number) | Baja | Tag input para strings; raw JSON para casos complejos |

## Rollback Plan

Revert commits del frontend + backend. El endpoint existente `GET /api/catalogos/<key>` no cambia su response — backward compatible. Los catálogos existentes no se modifican.

## Dependencies

None.

## Success Criteria

- [ ] CRUD funcional: crear, listar, editar valores, eliminar (con validación)
- [ ] `GET /api/catalogos/<key>/reglas` retorna reglas activas que referencian el key
- [ ] DELETE a catálogo con reglas activas retorna 409 + lista de reglas
- [ ] Página `/admin/catalogos` muestra tabla con catálogos y modal "Ver reglas"
- [ ] Tests backend pasan
