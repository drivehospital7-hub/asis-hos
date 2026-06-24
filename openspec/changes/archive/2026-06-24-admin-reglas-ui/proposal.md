# Proposal: Admin UI para Motor de Reglas

## Intent

F1 entregó el motor de reglas en DB con 3 reglas seed, engine evaluador y repositorio de evidencias. Pero gestionar reglas requiere SQL directo. F2 habilita una interfaz web para que usuarios no técnicos creen, editen, versionen y prueben reglas de negocio.

**Valor**: eliminar dependencia de SQL para mantenimiento de reglas, acelerar iteraciones de auditoría, y dar trazabilidad visible.

## Scope

### In Scope (F2.1 + F2.2)

- API RESTful completa: CRUD de reglas con auto-versionado, excepciones, consulta de evidencias/auditoría, y simulador
- Flask-admin templates server-rendered: listado con filtros, formulario de edición con árbol de condiciones, timeline de versiones, panel de excepciones, dashboard de evidencias, página de simulación
- Servicios SRP: `rule_service`, `exception_service`, `evidence_service`, `audit_service`, `simulator_service`
- Strict TDD: pytest para toda nueva lógica de servicios

### Out of Scope (Diferido a F3)

- Condition tree builder drag-and-drop (usará selects anidados en F2)
- React admin UI compleja (Flask templates vanilla)
- Permisos granulares por regla (deferido a mejoras del módulo auth)
- Multi-tenant

## Capabilities

### New Capabilities
- `admin-reglas-api`: Endpoints REST para CRUD de reglas, excepciones, versiones, consulta de evidencias/auditoría, y simulación dry-run
- `admin-reglas-ui`: Flask-admin templates para gestión visual de reglas (listado, edición, versiones, excepciones, simulador)

### Modified Capabilities
- `motor-reglas`: la API versiona reglas automáticamente (PUT → deprecate old + create new). El spec existente cubre el comportamiento del resolver; se agrega delta para el auto-versionado vía API.
- `evidencia-auditoria`: la API expone consulta de evidencias vía EvidenceRepository (ya existe, solo se wrappea como endpoint)

## Approach

- **API primero**: endpoints REST en `app/routes/reglas_api.py` (Blueprint con url_prefix `/api`) delegando a servicios en `app/services/reglas/`. Sigue el patrón exacto de `notas_api.py`.
- **Auto-versionado en PUT**: al actualizar una regla activa, la actual se marca `deprecated` y se crea una nueva versión con `estado=active`. La respuesta retorna ambos IDs.
- **Tree builder con selects encadenados**: el formulario permite elegir tipo de nodo (AND/OR/NOT/atómico) y operador mediante `<select>` anidados. Sin drag-and-drop, sin React.
- **Simulador**: subir Excel → el servicio ejecuta el engine contra las reglas DB y también los detectores legacy → compara resultados y muestra diff.
- **Template structure**: React page en `frontend/src/pages/admin-reglas/` con el mismo patrón que `catalogo/`: `index.html`, `main.tsx`, `page.tsx`. API client en `frontend/src/lib/api-reglas.ts`. Componentes shadcn/ui existentes. Vite multi-page con entry point en `vite.config.ts`.
- **Flask route**: `app/routes/reglas_admin.py` que renderiza `react_shell.html` con `entry_js` y `entry_css` del build de Vite, inyectando `__INITIAL_DATA__` con usuario y permisos.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/routes/reglas_api.py` | New | Blueprint `reglas_api` con url_prefix `/api/reglas` — endpoints REST |
| `app/routes/reglas_admin.py` | New | Blueprint `reglas_admin` — ruta que sirve React shell con `entry_js`/`entry_css` |
| `app/services/reglas/` | New | Package con 5 servicios: rule, exception, evidence, audit, simulator |
| `frontend/src/pages/admin-reglas/` | New | Página React con `page.tsx`, `main.tsx`, `index.html` (patrón catalogo) |
| `frontend/src/lib/api-reglas.ts` | New | API client tipado con fetch wrappers |
| `frontend/vite.config.ts` | Modified | Agregar entry point `src/pages/admin-reglas/index.html` |
| `app/__init__.py` | Modified | Registrar blueprints |
| `tests/reglas/` | New | Tests unitarios para servicios y rutas |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Auto-versionado rompe reglas activas durante seed migration | Low | `PUT` solo versiona al cambiar contenido relevante (nombre, condiciones, params). Versión actual sigue activa hasta que la nueva se crea. |
| Simulador lento con Excel grande | Medium | Limitar a primeras 100 filas del Excel. Documentar límite en UI. |
| Condition tree builder complejo de UX sin JS | Medium | Usar selects con datos cargados desde API, POST del árbol serializado como JSON. |

## Rollback Plan

- **Por endpoint**: cada endpoint es independiente. Si un endpoint falla, se puede revertir ese solo sin tocar el resto.
- **Por deploy completo**: desregistrar los blueprints en `app/__init__.py`, eliminar archivos de rutas y servicios, y re-deploy. Reglas en DB no se modifican — el engine sigue funcionando sin la UI.
- **Auto-versionado**: si el PUT falla, la regla original permanece intacta (transacción envuelve ambas operaciones: deprecate + create).

## Dependencies

- F1 tables (reglas, condiciones, excepciones, evidencias, resultados_auditoria) — ya existen y están seedeadas
- `EvidenceRepository` — ya existe, se wrappea como endpoint
- `app/database.py` (get_db) — ya existe, patrón usado en `notas_api.py`

## Success Criteria

- [ ] API endpoints responden con formato `{"status", "data", "errors"}` consistente
- [ ] PUT versiona correctamente: regla anterior → deprecated, nueva versión → active
- [ ] Simulador muestra diff entre engine DB y detectores legacy en < 5s para 100 filas
- [ ] Tests pasan: `python -m pytest tests/reglas/ -v`
- [ ] Flask templates renderizan sin errores y heredan de `base.html`
