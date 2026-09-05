# Design: Cronograma Bacteriólogas

## Technical Approach

Grid-based schedule manager (bacteriólogas × días del mes) con persistencia JSON. Sigue el patrón CRUD de `abiertas_urgencias` pero con un modelo de datos fundamentalmente distinto: celdas con códigos de turno (CE, PYM, N, L, D) en vez de columnas horarias. Expone un endpoint específico para consultar quién está asignado a CE/PYM en un día dado.

**⚠️ Data model correction**: La proposal y spec asumieron el modelo 3-columnas (mañana/tarde/noche) de `abiertas_urgencias`. El formato real de negocio es una grilla 2D (bacteriólogas como filas, días como columnas). Este diseño resuelve esa divergencia.

## Architecture Decisions

### Decision: Grid (bacterióloga × día) vs 3-turnos (mañana/tarde/noche)

| Opción | Tradeoff |
|--------|----------|
| Grid bacteriólogas × días | ✅ Mapea exactamente al TSV que pegan desde Excel; consulta "quién tiene CE/PYM hoy" es directa |
| 3-turnos (proposal) | ❌ No corresponde al formato real de datos; requeriría transformación extra |

**Decisión**: Grid model. JSON con `{dia, turnos: {KAREN: "C", ...}}`.

### Decision: Parseo con detección de FECHA header

El TSV pegado tiene 2 filas de encabezado (FECHA con números de día, DIA con abreviaturas). Se detecta la fila que contiene "FECHA" como marcador de inicio, se extraen los días de esa fila, y se parsean las filas subsiguientes como `nombre \t codigo \t codigo ...`.

### Decision: Match por primer nombre contra PROFESIONALES_URGENCIAS

Los nombres en el TSV son el primer nombre (KAREN, VALENTINA, etc.). Se resuelven contra `PROFESIONALES_URGENCIAS` donde `tipo == "BACTERIOLOGA"`, extrayendo el primer token del nombre completo como key.

### Decision: Endpoint dedicado para turno del día

`GET /api/turno` recibe `dia`, `mes`, `anio` opcionales (default HOY) y devuelve las bacteriólogas cuyo código contiene "CE" o "PYM" (cubre CE, PYM, CE/PYM, PYM/N).

## Data Flow

```
Usuario pega TSV → Frontend (parseo.ts)
  → parsearTexto() → {mes, anio, dias: [{dia, turnos}]}
  → POST /api → Service.save_horario() → cronograma_bacteriologas.json

GET /api/turno?dia=5 → Service.get_turno_del_dia()
  → filtra dias[dia-1].turnos donde valor contiene CE|PYM
  → devuelve {bacteriologas: [{nombre, codigo}]}
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/routes/cronograma_bacteriologas.py` | Create | Blueprint: GET/POST /api + GET /api/turno. Decorador @admin_requerido. |
| `app/services/cronograma_bacteriologas_service.py` | Create | CRUD JSON + get_turno_del_dia(). Mismo patrón que abiertas_urgencias_service. |
| `app/__init__.py` | Modify | `register_blueprint(cronograma_bp, url_prefix="/cronograma-bacteriologas")` |
| `frontend/src/pages/cronograma-bacteriologas/index.html` | Create | Shell HTML (entry point) |
| `frontend/src/pages/cronograma-bacteriologas/main.tsx` | Create | Entry React con AppLayout |
| `frontend/src/pages/cronograma-bacteriologas/page.tsx` | Create | Grid table + parse card + turno de hoy + save/delete |
| `frontend/src/pages/cronograma-bacteriologas/parseo.ts` | Create | `parsearTexto()`: detecta "FECHA" header, parsea TSV grid → JSON |
| `frontend/src/pages/cronograma-bacteriologas/constants.ts` | Create | NOMBRE_MAP (5 bacteriólogas desde PROFESIONALES_URGENCIAS) |
| `frontend/vite.config.ts` | Modify | Agregar `rollupOptions.input` entry |
| `frontend/src/components/app-sidebar.tsx` | Modify | Nav item "Cronograma Bacteriólogas", permiso `*` |

## Interfaces / Contracts

```json
// POST /api body
{"dias": [{"dia": 1, "turnos": {"KAREN": "C", "VALENTINA": "N", "KAROL": "L", "ALEJANDRA": "CE/PYM"}}]}

// GET /api/turno?dia=5 response
{"status": "success", "data": {"bacteriologas": [{"nombre": "MADROÑERO BURBANO KAREN LIZETH", "codigo": "CE"}], "dia": 5}}

// JSON schema
{"mes": 6, "anio": 2026, "dias": [{dia: int, turnos: {[primer_nombre]: string}}], "total_dias": int}
```

```typescript
// parseo.ts
function parsearTexto(texto: string): {
  mes: number;
  anio: number;
  dias: Array<{ dia: number; turnos: Record<string, string> }>;
} | null;
```

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | `parsearTexto()` with valid TSV, missing header, empty cells | Jest (`*.test.ts`) |
| Unit | `get_turno_del_dia()` with CE, PYM, CE/PYM, empty day | pytest + Flask test client |
| Unit | Service CRUD: save, load (same month), load (different month), delete | pytest |
| Integration | Full flow: POST → GET → GET /api/turno → DELETE | pytest with temp JSON |

## Migration / Rollout

No migration required. Feature autónoma sin impacto en módulos existentes.

## Open Questions

None. El diseño resuelve la divergencia proposal/spec → requisito real de negocio.
