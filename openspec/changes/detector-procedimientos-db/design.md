# Design: Detector transversal de procedimientos contratados

## Technical Approach

Detector `detect_cups_sin_contrato(data_sheet, indices) -> list[dict]` que pre-carga desde PostgreSQL el set de pares `(cod_contrato, cups)` contratados mediante JOIN de 5 tablas, más un dict `cod_contrato → eps_name` para el mensaje de error. Por cada fila del Excel normaliza y verifica pertenencia al set. Sigue exactamente el patrón de `app/services/urgencias/codigos_sin_db.py` (try/except DB, pre-load query, row-by-row scan).

## Architecture Decisions

### Decision: Nombre del detector

| Opción | Voto |
|--------|------|
| `detect_cups_sin_contrato` | ✅ Elegido |
| `detect_procedimiento_no_contratado` | ❌ Más genérico pero menos preciso |
| `detect_cups_no_contratados` | ❌ Similar |

**Rationale**: El spec usa "CUPS sin contrato" como mensaje de error. El nombre debe coincidir con el lenguaje del negocio.

### Decision: Archivo en `transversales/`

**Choice**: `app/services/transversales/procedimiento_contratado.py`

**Rationale**: La regla aplica a TODAS las áreas. Sigue el patrón de `codigo_entidad.py` y los detectores existentes en `app/services/transversales/`. El nombre del archivo refleja el dominio del negocio (procedimiento contratado), no el detector específico (que puede haber varios en el futuro).

### Decision: Pre-load con dos estructuras

**Choice**: `set[(cod_contrato_norm, cups_norm)]` + `dict[cod_contrato_norm, eps_name]`

**Rationale**: El set permite O(1) lookup por fila. El dict extra resuelve el nombre de la EPS en el mensaje de error sin pegar por cada fila. Se obtienen ambos del mismo JOIN query con una sola iteración.

### Decision: JOIN chain

**Choice**: `eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento` (5 tablas)

**Rationale**: Es la cadena real que define qué procedimientos están contratados para cada EPS en el sistema. No es posible simplificarla porque la relación no es directa: una EPS puede tener múltiples notas hoja, cada nota hoja tiene múltiples notas técnicas, y cada nota técnica apunta a un procedimiento.

### Decision: Integración Odontología/Equipos Básicos

**Choice**: Agregar parámetro `cupssincontrato` a `build_odontologia_normalized_rows()` y pasar el resultado del detector desde `detect_all.py`

**Rationale**: Odontología y Equipos Básicos NO usan el builder compartido `build_normalized_rows()`. Usan `build_odontologia_normalized_rows()` con parámetros nombrados. Hay dos opciones: (a) agregar un parámetro nuevo, o (b) migrar a error_groups. La opción (a) es mínima y consistente con el patrón existente. La migración a error_groups sería un refactor más grande fuera del scope.

## Data Flow

```
PostgreSQL                          Excel
    │                                  │
    │  JOIN 5 tablas                    │ openpyxl row-by-row
    │  eps_contratado → ... → proc      │ (row >= 2)
    ▼                                  ▼
┌─────────────────┐            ┌──────────────┐
│  Pre-load (1x)  │            │ Por cada fila │
│                  │            │              │
│ set_validos      │◄───────────│ leer         │
│ dict_eps_names   │   lookup   │ cod_entidad  │
│                  │            │ + codigo     │
└─────────────────┘            │ normalizar   │
         │                     │ strip.upper  │
         ▼                     └──────┬───────┘
    ┌──────────────────┐              │
    │ Si (cod, cups)   │◄─────────────┘
    │ NOT in set       │
    │ → agregar error  │
    └──────────────────┘
         │
         ▼
    ┌──────────────────┐
    │ error_groups[     │
    │  "Cups Sin        │
    │  Contrato"        │
    │ ] = problemas     │
    └──────────────────┘
         │
         ├──→ build_normalized_rows()  (Urg/Hosp/Int/Amb)
         └──→ build_odontologia_normalized_rows()   (Odont/EB)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/transversales/procedimiento_contratado.py` | Create | Detector `detect_cups_sin_contrato()` con pre-load DB y scan de filas |
| `app/services/transversales/__init__.py` | Modify | Exportar `detect_cups_sin_contrato` |
| `app/services/normalized_rows.py` | Modify | Agregar bloque "Cups Sin Contrato" en `build_normalized_rows()` |
| `app/services/odontologia/normalized_rows.py` | Modify | Agregar parámetro `cups_sin_contrato` en `build_odontologia_normalized_rows()` |
| `app/services/urgencias/detect_all.py` | Modify | Llamar detector + agregar a error_groups y resultado |
| `app/services/hospitalizacion/detect_all.py` | Modify | Igual |
| `app/services/intramural/detect_all.py` | Modify | Igual |
| `app/services/ambulatoria/detect_all.py` | Modify | Igual |
| `app/services/odontologia/detect_all.py` | Modify | Llamar detector + pasar a `build_odontologia_normalized_rows()` |
| `app/services/equipos_basicos/detect_all.py` | Modify | Igual |
| `tests/services/test_transversales_procedimiento_contratado.py` | Create | Tests unitarios con workbook mockeado |

## Interfaces / Contracts

### Detector function

```python
def detect_cups_sin_contrato(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Retorna problemas de CUPS no contratados para la entidad.

    Cada dict:
        "factura": str,
        "codigo": str,                  # CUPS normalizado
        "procedimiento": str,           # nombre del procedimiento (del Excel)
        "codigo_entidad_cobrar": str,   # código entidad normalizado
        "entidad": str,                 # nombre EPS (resuelto desde DB)
        "problema": str,                # "CUPS {codigo} no contratado para {cod_entidad}, {entidad}"
    """
```

### normalized_rows — bloque nuevo en `build_normalized_rows()`

```python
# --- Cups Sin Contrato ---
for item in error_groups.get("Cups Sin Contrato", []):
    factura = item.get("factura", "")
    codigo = item.get("codigo", "")
    proc = item.get("procedimiento", "")
    cod_ent = item.get("codigo_entidad_cobrar", "")
    entidad = item.get("entidad", "")
    rows.append({
        "tipo_error": "Cups Sin Contrato",
        "factura": factura,
        "fec_factura": _get_fec_factura(factura),
        "responsable_cierra": _get_responsable(factura),
        "descripcion": item.get("problema", ""),
        "procedimiento": _build_procedimiento(codigo, proc),
        "detalle": f"Entidad: {cod_ent}, {entidad}",
        "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
    })
```

### normalized_rows odontología — nuevo parámetro

```python
def build_odontologia_normalized_rows(
    ...,
    cups_sin_contrato: list[dict] | None = None,
) -> list[dict[str, str]]:
```

### Pre-load query

```python
# Chain: eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento
query = (
    db.query(EpsContratado.cod_contrato, EpsContratado.eps, Procedimiento.cups)
    .join(EpsNota, EpsNota.id_eps_contratado == EpsContratado.id)
    .join(NotaHoja, NotaHoja.id == EpsNota.id_nota_hoja)
    .join(NotasTecnicas, NotasTecnicas.id_nota_hoja == NotaHoja.id)
    .join(Procedimiento, Procedimiento.id == NotasTecnicas.id_procedimiento)
    .distinct()
    .all()
)
valid_pairs: set[tuple[str, str]] = set()
eps_names: dict[str, str] = {}
for cod_contrato, eps, cups in query:
    key = (cod_contrato.strip().upper(), cups.strip().upper())
    valid_pairs.add(key)
    if cod_contrato not in eps_names:
        eps_names[cod_contrato] = eps
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Detector con datos mockeados | Monkeypatch `SessionLocal` para retornar pares válidos conocidos. Verificar que filas válidas NO generan error y filas inválidas SÍ. |
| Unit | DB no disponible | Monkeypatch `SessionLocal` para levantar Exception → verificar `[]` + logger.warning |
| Unit | Columnas faltantes | Pasar indices sin `codigo_entidad_cobrar` o sin `codigo` → verificar `[]` |
| Unit | Normalización en build_normalized_rows | Crear error_groups con key "Cups Sin Contrato" → verificar salida formateada |
| Unit | Normalización en build_odontologia_normalized_rows | Pasar lista de dicts → verificar salida |

## Migration / Rollout

No migration required. El detector es additive: si falla la DB, retorna vacío sin crash. Si falla la consulta, no afecta filas existentes.

## Open Questions

- [x] **Nombre del detector** → Resuelto: `detect_cups_sin_contrato`
- [x] **Áreas** → Resuelto: TODAS (Urg, Hosp, Int, Amb, Odont, EB)
- [x] **Incluir nombre de EPS** → Resuelto: sí, con dict separado
