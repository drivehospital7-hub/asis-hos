# AGENTS.md — Control System

> **Instrucciones para agentes IA.** Lee COMPLETO antes de escribir código.

---

## Contexto

**Sistema de Control de Facturación Médica** para EPS MALLAMAS (indígena).

- Procesa archivos Excel de facturas médicas (odontología)
- Detecta problemas: decimales, duplicados, convenios incorrectos
- Genera hojas de cruce y revisión con formato condicional

**Stack**: Flask + Polars (lectura) + openpyxl (escritura) + waitress (prod)

---

## Arquitectura

```
app/
├── routes/       # Endpoints HTTP (SOLO delegan)
├── services/     # Lógica de negocio (SRP)
├── utils/        # Helpers reutilizables
├── constants.py  # Valores compartidos (ÚNICO lugar)
└── data/
    ├── input/    # Excel de entrada
    └── output/   # Excel procesados
```

### Reglas (NO NEGOCIABLES)

| Regla | Descripción |
|-------|-------------|
| **Routes = delegadores** | Reciben request → llaman servicio → retornan respuesta. CERO lógica. |
| **Services = SRP** | Una responsabilidad por servicio. Si hace dos cosas, dividir. |
| **No hardcodear** | Valores compartidos van en `constants.py` |

---

## Response Format (OBLIGATORIO)

```python
{
    "status": "success" | "error",  # NUNCA "warning"
    "data": {},                      # siempre dict
    "errors": []                     # siempre list
}
```

---

## Código

| Regla | Ejemplo |
|-------|---------|
| Funciones < 50 líneas | ✅ |
| Nombres descriptivos | `get_excel_column_headers` ✅ / `get_cols` ❌ |
| Clases: PascalCase | `DevConfig` |
| Funciones: snake_case | `process_excel` |
| Constantes: UPPER_SNAKE | `ALLOWED_EXCEL_SUFFIXES` |

### Imports (orden)

```python
# 1. stdlib
from pathlib import Path

# 2. terceros
import polars as pl

# 3. locales
from app.services.excel_column_headers import get_excel_column_headers
```

### Logging (siempre usar)

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Procesando: %s", filename)
logger.exception("Error procesando")  # en except
```

---

## Workflow

### Antes de codificar

1. Entender el requerimiento
2. Proponer approach (NO asumir)
3. Esperar validación
4. Si es cambio grande → SDD

### Reglas críticas

- No generar múltiples archivos sin aprobación
- No modificar estructura sin autorización
- No asumir requerimientos — preguntar
- Explicar antes de codificar

---

## Anti-Patrones

```python
# ❌ Lógica en routes
@bp.route("/export")
def export():
    df = pl.read_excel(file)
    # 200 líneas...

# ✅ Routes delgadas
@bp.route("/export")
def export():
    return export_service.process(request.form)
```

```python
# ❌ Constantes duplicadas
SHEET = "CruceFacturas"  # archivo A
SHEET = "CruceFacturas"  # archivo B

# ✅ Centralizar
from app.constants import CRUCE_FACTURAS_SHEET
```

---

## Archivos Clave

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `app/services/exporter.py` | Orquestador de exportación | ✅ |
| `app/services/cruce_sheet.py` | Hoja CruceFacturas | ✅ |
| `app/services/revision_sheet.py` | Detección de problemas | ✅ |
| `app/utils/column_filter.py` | Filtrado de columnas | ✅ |
| `app/utils/formatting.py` | Formato condicional | ✅ |
| `app/services/excel_column_headers.py` | Lee headers Excel (Polars) | ✅ |
| `app/utils/input_data.py` | Paths seguros | ✅ |

---

## Ejecución

```bash
# Desarrollo
mkdir -p logs && python run_dev.py

# Producción  
python run_prod.py
```

---

## Referencias

- **CONVENTIONS.md** → Reglas de NEGOCIO (validaciones, procedimientos, colores)
- **.atl/skill-registry.md** → Skills para sub-agentes
- **Engram** → `sdd/reorganizacion-control-system/` para plan de refactor
