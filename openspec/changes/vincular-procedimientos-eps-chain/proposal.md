# Proposal: Vincular Procedimientos a EPS (cadena SQLite)

## Intent

Permitir desde `/catalogo` crear la cadena completa EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento. Hoy el modal "Ver Procedimientos" es solo lectura — no hay forma de vincular un CUPS a una EPS desde la UI.

## Scope

### In Scope
- Endpoint `POST /api/eps/<id>/vincular-procedimiento` (transacción atómica)
- Pestaña "Notas Hoja" (SQLite) con CRUD para NotaHoja
- Formulario en modal "Ver Procedimientos": select NotaHoja + select Procedimiento + input tarifa
- Funciones API client en `api-catalogo.ts`
- Incluir `id_nota_hoja` en respuesta chain view
- Backend tests + frontend API client tests

### Out of Scope
- CRUD directo para EpsNota (lo maneja el endpoint compuesto)
- CRUD directo para NotasTecnicas (lo maneja el endpoint compuesto)
- Import/export masivo
- Renombrar columna `tariff` → `tarifa` (deuda técnica documentada)

## Capabilities

### New Capabilities
- `vincular-procedimientos-eps`: Vincular procedimientos CUPS a EPS mediante la cadena de relaciones SQLite (NotaHoja, EpsNota, NotasTecnicas)

### Modified Capabilities
None

## Approach

**Backend**: Nuevo endpoint `POST /api/eps/<id>/vincular-procedimiento` en `notas_api.py`. Acepta `{ id_nota_hoja, id_procedimiento, tarifa }`. En una transacción: (1) crea EpsNota con `id_eps_contratado` + `id_nota_hoja`, (2) crea NotasTecnicas con `id_procedimiento` + `id_nota_hoja` + `tarifa`. Rollback si falla algo.

**Frontend**: 4ta pestaña "Notas Hoja" con tabla CRUD (único campo `nota`). En modal "Ver Procedimientos", formulario al final con dropdowns: NotaHoja (GET /api/notas-hoja), Procedimiento (GET /api/procedimientos), input tarifa + botón "Vincular". Llama al endpoint compuesto.

**Fix**: En `get_procedimientos_por_eps()` agregar `id_nota_hoja` al dict de respuesta.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/routes/notas_api.py` | Modified | +1 endpoint compuesto; fix id_nota_hoja en chain |
| `app/services/eps_contratado_crud.py` | Modified | +id_nota_hoja en dict retornado |
| `frontend/src/pages/catalogo/page.tsx` | Modified | +pestaña NotasHoja, +form en modal chain |
| `frontend/src/lib/api-catalogo.ts` | Modified | +tipos NotaHoja, +fetchNotasHoja, +vincularProcedimiento |
| `frontend/src/pages/catalogo/__tests__/api-catalogo.test.ts` | Modified | +tests nuevas funciones |
| `tests/routes/test_vincular_procedimiento.py` | New | Tests endpoint compuesto |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `tariff`/`tarifa` mismatch en NotasTecnicas | Med | Endpoint usa `tarifa` en request/response; CRUD mapea internamente. Tech debt documentado. |
| EpsNota duplicado (mismo id_nota_hoja + id_eps_contratado) | Baja | Validar duplicado antes de insertar, error 400 |

## Rollback Plan

Revert commit del endpoint compuesto + pestaña NotasHoja + formulario. El fix de `id_nota_hoja` en chain response es backward-compatible — no requiere rollback separado.

## Dependencies

None — endpoints CRUD individuales ya existen en `notas_api.py`.

## Success Criteria

- [ ] `POST /api/eps/<id>/vincular-procedimiento` crea EpsNota + NotasTecnicas atómicamente
- [ ] Rollback completo si falla cualquiera de los dos inserts
- [ ] Pestaña "Notas Hoja" lista, crea, edita, elimina registros
- [ ] Formulario en "Ver Procedimientos" permite vincular procedimiento a EPS
- [ ] Chain response incluye `id_nota_hoja`
- [ ] Tests backend + frontend pasan
