# Design: Vincular Procedimientos a EPS (cadena SQLite)

## Technical Approach

Nuevo endpoint compuesto `POST /api/eps/<id>/vincular-procedimiento` con transacción atómica manual (sin reutilizar CRUDs existentes que hacen `commit` propio). Pestaña "Notas Hoja" replicando el patrón de tabla + modal de las tabs existentes. Formulario inline en el modal "Ver Procedimientos" con dropdowns cargados al abrir el modal.

## Architecture Decisions

### Decision 1: Atomicidad del endpoint compuesto

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Reusar CRUDs existentes (`eps_nota_crud.create` + `notas_tecnicas_crud.create`) | Cada CRUD hace `db.commit()` individual — si el segundo falla, el primero ya persiste. | ❌ |
| Nuevo service con `db.begin()` / `try: db.commit() / except: db.rollback()` | Control total de la transacción. Sin duplicar lógica de validación pesada. | ✅ |

**Rationale**: Los CRUDs existentes llaman `db.commit()` internamente. Para atomicidad necesitamos un service nuevo (`vincular_procedimiento_service.py`) que maneje ambos inserts en una sola transacción. Valida duplicados inline (misma lógica que los CRUDs pero sin commit intermedio), luego `db.commit()`. Si algo falla, `db.rollback()`.

### Decision 2: Form UX en "Ver Procedimientos"

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Sub-modal separado | Más clicks, más anidación de overlays. | ❌ |
| Inline al final del modal actual | Un solo modal. El form vive abajo de la tabla. Carga dropdowns al abrir el modal. | ✅ |

**Rationale**: El modal chain view ya está abierto con la tabla de procedimientos. Agregar el form al final es el mínimo cambio de UX — dos selects + input + botón. Si se abre un sub-modal, hay dos capas de overlay y más estados que manejar.

### Decision 3: Carga de dropdowns

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Precargar al montar EpsTab | Datos disponibles siempre, pero fetch innecesario si el usuario nunca abre el modal. | ❌ |
| Cargar al abrir el modal chain view | Un fetch adicional (paralelo a `fetchProcedimientosPorEps`). Datos frescos siempre. | ✅ |

**Rationale**: Son dos GETs livianos (`/api/notas-hoja`, `/api/procedimientos`) que se disparan cuando el usuario hace clic en "Ver Procedimientos". Se ejecutan en paralelo con la carga de la cadena. No hay penalización si el usuario nunca abre el modal.

### Decision 4: Inconsistencia `tariff` / `tarifa`

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Renombrar columna DB a `tarifa` | Migración de schema, afecta queries existentes. Out of scope (proposal). | ❌ |
| Endpoint recibe `tarifa`, CRUD mapea internamente (ya existe) | Deuda técnica documentada. Consistente con el resto del código. | ✅ |

**Rationale**: El modelo `NotasTecnicas` tiene `tariff` en DB, pero todos los endpoints y el CRUD usan `tarifa`. El endpoint compuesto acepta `tarifa` y lo pasa al CRUD que mapea a `tariff`. Mismo patrón existente.

## Data Flow

```
POST /api/eps/{id}/vincular-procedimiento
  Body: { id_nota_hoja, id_procedimiento, tarifa }

  notas_api.py
    │
    ├─ VincularProcedimientoService.ejecutar(db, eps_id, data)
    │     │
    │     ├─ Valida: eps existe, nota_hoja existe, procedimiento existe
    │     ├─ Valida: EpsNota duplicado? → error 400
    │     ├─ Valida: NotasTecnicas duplicado? → error 400
    │     │
    │     ├─ Crea EpsNota(id_eps_contratado, id_nota_hoja)  → db.add()
    │     ├─ Crea NotasTecnicas(id_procedimiento, id_nota_hoja, tariff=tarifa) → db.add()
    │     │
    │     └─ db.commit()  — o —  db.rollback() si falla algo
    │
    └─ Retorna { eps_nota, notas_tecnicas }
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/vincular_procedimiento_service.py` | Create | Service con transacción atómica para el endpoint compuesto |
| `app/routes/notas_api.py` | Modify | +`POST /api/eps/<id>/vincular-procedimiento` |
| `app/services/eps_contratado_crud.py` | Modify | +`"id_nota_hoja"` en dict de `get_procedimientos_por_eps()` |
| `frontend/src/lib/api-catalogo.ts` | Modify | +`NotaHoja` type, +`fetchNotasHoja()`, +`vincularProcedimiento()`, +`id_nota_hoja` en `EpsProcedimientosChain` |
| `frontend/src/pages/catalogo/page.tsx` | Modify | +Tab "Notas Hoja" (CRUD), +formulario en modal chain view |
| `frontend/src/pages/catalogo/__tests__/api-catalogo.test.ts` | Modify | +tests para `fetchNotasHoja`, `vincularProcedimiento` |
| `tests/routes/test_vincular_procedimiento.py` | Create | Tests de integración para el endpoint compuesto |

## Interfaces / Contracts

```python
# POST /api/eps/<int:eps_id>/vincular-procedimiento
Request:
  {
    "id_nota_hoja": int,      # FK a nota_hoja.id
    "id_procedimiento": int,  # FK a procedimiento.id
    "tarifa": number          # se mapea a tariff en DB
  }

Success 201:
  {
    "status": "success",
    "data": {
      "eps_nota": { "id": int, "id_nota_hoja": int, "id_eps_contratado": int },
      "notas_tecnicas": { "id": int, "id_procedimiento": int, "id_nota_hoja": int, "tarifa": float }
    },
    "errors": []
  }

Error 400 (duplicado/validación):
  { "status": "error", "data": {}, "errors": ["mensaje"] }

Error 404 (eps no existe):
  { "status": "error", "data": {}, "errors": ["No existe EPS con id: {id}"] }
```

```typescript
// api-catalogo.ts — nuevos tipos y funciones
export interface NotaHoja {
  id: number;
  nota: string;
}

// ✏️ Modificar EpsProcedimientosChain.procedimientos
// Agregar: id_nota_hoja: number;
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Backend Integration | POST endpoint con datos válidos | Crear EpsContratado + NotaHoja + Procedimiento, llamar endpoint, verificar ambos registros creados |
| Backend Integration | POST con EPS inexistente | Esperar 404 |
| Backend Integration | POST con duplicado | Insertar 2 veces mismo combo → esperar 400 en segunda |
| Backend Integration | Rollback en fallo | Simular error en segundo insert, verificar que primero NO persiste |
| Frontend Unit | `fetchNotasHoja` | Mock fetch, verificar GET /api/notas-hoja y parseo |
| Frontend Unit | `vincularProcedimiento` | Mock fetch, verificar POST /api/eps/{id}/vincular-procedimiento con body correcto |
| Frontend Unit | `EpsProcedimientosChain` con `id_nota_hoja` | Actualizar mock test existente |

## Migration / Rollout

No migration required. El fix de `id_nota_hoja` en chain response es backward-compatible (campo nuevo en dict existente). El endpoint compuesto es nuevo — no afecta operación existente.

## Open Questions

- [ ] None — todas las decisiones están resueltas en el proposal y el codebase review.
