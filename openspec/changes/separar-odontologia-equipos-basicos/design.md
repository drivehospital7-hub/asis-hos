# Design: Separar Odontología de Equipos Básicos

## Technical Approach

**Separación completa**: Crear Blueprint, React page, constantes y permiso nuevos para Equipos Básicos (EB), luego eliminar el acoplamiento vía checkbox + booleano en dispatcher.

## Architecture Decisions

| # | Decisión | Alternativa | Rationale |
|---|----------|-------------|-----------|
| 1 | Nuevo Blueprint `odontologia_equipos_basicos_bp` en `app/routes/odontologia_equipos_basicos.py` | Meter en ruta existente | Mismo patrón que `urgencias`, `derechos`, etc. — cero sorpresas |
| 2 | React page copia de `odontologia/page.tsx` con profesionales EB | Template legacy Flask | React es el target; la template legacy se depreca |
| 3 | `exporter.py`: eliminar `equipos_basicos: bool`, caller pasa `area=AREA_EQUIPOS_BASICOS` | Mantener bool | El bool era la fuente del acoplamiento. `area` ya existe como parámetro nominal |
| 4 | Constantes EB en `app/constants/equipos_basicos.py` + re-export desde `__init__.py` | Dejarlas mezcladas | SRP: cada dominio su propio módulo. No rompe imports existentes por el wildcard re-export |
| 5 | `odontologia_equipos_basicos` en `ALLOWED_PERMISOS` sin migración automática | Migrar legacy | Decisión explícita del usuario — riesgos conocidos |
| 6 | Eliminar checkbox EB + JS condicional de `excel_headers.html` | Ocultarlo condicionalmente | Si EB ya no se procesa aquí, el checkbox no tiene sentido |

## Data Flow

```
POST /odontologia-equipos-basicos/
  → odontologia_equipos_basicos_bp.export_cruce_eb()
  → detect_problems_only(filename, area=AREA_EQUIPOS_BASICOS, ...)
    → _do_detect_problems(area=AREA_EQUIPOS_BASICOS)
      → detect_all_problems_equipos_basicos(sheet, indices, ...)
        → detectores transversales + EB-specific
POST /odontologia/
  → excel_headers_bp.export_cruce_facturas()
  → detect_problems_only(filename, area=AREA_ODONTOLOGIA, ...)  ← sin equipos_basicos flag
    → _do_detect_problems(area=AREA_ODONTOLOGIA)
      → detect_all_problems_odontologia(sheet, indices, ...)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/routes/odontologia_equipos_basicos.py` | **Create** | Blueprint GET (React shell) + POST (upload+detect) |
| `app/constants/equipos_basicos.py` | **Create** | Mover: `PROFESIONALES_EQUIPOS_BASICOS`, thresholds EB, `CENTRO_COSTO_EQUIPOS_BASICOS`, `EQUIPOS_BASICOS_REVISION_HEADERS`, `EQUIPOS_BASICOS_COLUMNS_TO_KEEP` |
| `frontend/src/pages/odontologia-equipos-basicos/` | **Create** | React page: `page.tsx`, `index.html`, `main.tsx` — adaptada de odontología |
| `app/services/exporter.py` | **Modify** | Eliminar `equipos_basicos: bool` de params; usar `area` directamente |
| `app/services/exporter.py` | **Modify** | Simplificar `_do_detect_problems`: eliminar `area_effective`, eliminar `or equipos_basicos` (línea 266) |
| `app/routes/excel_headers.py` | **Modify** | Eliminar `equipos_basicos = request.form.get(...)` (línea 84) y su log |
| `app/constants/odontologia.py` | **Modify** | Eliminar bloques `# EQUIPOS BÁSICOS` (líneas 202-280) |
| `app/constants/columnas.py` | **Modify** | Eliminar `CENTRO_COSTO_EQUIPOS_BASICOS`, `EQUIPOS_BASICOS_REVISION_HEADERS`, `EQUIPOS_BASICOS_COLUMNS_TO_KEEP` |
| `app/constants/base.py` | **Modify** | Agregar `odontologia_equipos_basicos` a `ALLOWED_PERMISOS` |
| `app/constants/__init__.py` | **Modify** | Agregar `from app.constants.equipos_basicos import *` |
| `app/__init__.py` (factory) | **Modify** | Import + register blueprint con `url_prefix="/odontologia-equipos-basicos"` |
| `app/templates/excel_headers.html` | **Modify** | Eliminar checkbox EB (líneas 89-95), eliminar `actualizarReglasModal()` (líneas 774-858) |
| `app/templates/base.html` | **Modify** | Agregar `odontologia_equipos_basicos` endpoint al nav_items dict y endpoint_map |
| `app/templates/home.html` | **Modify** | Agregar card EB con permiso `odontologia_equipos_basicos` |
| `app/templates/usuarios.html` | **Modify** | Agregar checkbox `odontologia_equipos_basicos` |
| `frontend/src/components/app-sidebar.tsx` | **Modify** | Agregar nav item EB con permiso `odontologia_equipos_basicos` |
| `frontend/src/pages/usuarios/page.tsx` | **Modify** | Agregar `odontologia_equipos_basicos` a `ALL_PERMISOS` |
| `app/routes/home.py` | **No change** | No tocar — el dashboard React usa initial_data de permisos, se adapta solo |
| `app/services/equipos_basicos/detect_all.py` | **No change** | Detectores no se modifican, solo cambia quién llama |
| `app/routes/urgencias.py` | **No change** | No afectado |

## Interfaces / Contracts

```python
# exporter.py — new signature
def detect_problems_only(
    *,
    filename: str,
    sheet_name: str | None = None,
    area: str = AREA_ODONTOLOGIA,          # ← unchanged, but callers pass the right value
    profesional: str = "",
    dias: list[int] | None = None,
    todos_profesionales_dias: dict[str, list[int]] | None = None,
    validar_centro_costo: bool = False,
    # ← equipos_basicos param REMOVED
) -> tuple[dict[str, Any], int]:

# New route — follows excel_headers.py pattern
odontologia_equipos_basicos_bp = Blueprint("odontologia_equipos_basicos", __name__)

@odontologia_equipos_basicos_bp.get("/")
@permiso_requerido("odontologia_equipos_basicos")
def excel_headers_react(): ...

@odontologia_equipos_basicos_bp.post("/")
@rate_limit(1, 120)
def export_cruce_eb():
    # reads file, calls detect_problems_only(area=AREA_EQUIPOS_BASICOS)
```

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | New route GET returns React shell with correct permiso | `app.test_client().get("/odontologia-equipos-basicos/")` → 200, template rendered |
| Unit | New route POST processes an EB Excel | Mock file upload → assert `detect_problems_only` called with `area=AREA_EQUIPOS_BASICOS` |
| Unit | `exporter.py` rejects `equipos_basicos` kwarg | Call without param → works; call with param → TypeError |
| Unit | Constant extraction: imports work | `from app.constants import PROFESIONALES_EQUIPOS_BASICOS` |
| Integration | Full roundtrip: POST → JSON response | Real Excel file → assert status + error list |
| E2E | Sidebar shows EB entry for new permiso | Login with `odontologia_equipos_basicos` → see EB link, NOT odontologia |
| Regression | All existing tests pass | `pytest` sin regresiones |

## Migration / Rollout

No migration required. El permiso `odontologia_equipos_basicos` se asigna manualmente a usuarios que necesiten EB. El permiso legacy `equipos_basicos` sigue funcionando para "Ordenado y Facturado". Rollback: revertir commits individualmente por capa.
