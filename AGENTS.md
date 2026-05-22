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
├── constants/       # Constantes por dominio (5 módulos: base, columnas, colores, odontologia, urgencias)
├── routes/          # Endpoints HTTP (SOLO delegan)
├── services/
│   ├── transversales/     # Reglas compartidas entre áreas (decimales, tipo_doc, etc.)
│   │   └── detectores parametrizados (ruta_duplicada, cantidades_anomalas, etc.)
│   ├── odontologia/       # Detectores + orquestador detect_all.py
│   ├── urgencias/         # Detectores + orquestador detect_all.py
│   ├── equipos_basicos/   # Detectores + orquestador detect_all.py
│   ├── exporter.py        # Orquestador de exportación
│   ├── cruce_sheet.py     # Hoja CruceFacturas
│   └── ...                # Otros servicios (genderize, derechos, etc.)
├── utils/           # Helpers reutilizables
└── data/
    ├── input/       # Excel de entrada
    └── output/      # Excel procesados
```

### Reglas (NO NEGOCIABLES)

| Regla                          | Descripción                                                               |
| ------------------------------ | ------------------------------------------------------------------------- |
| **Routes = delegadores**       | Reciben request → llaman servicio → retornan respuesta. CERO lógica.      |
| **Services = SRP**             | Una responsabilidad por servicio. Si hace dos cosas, dividir.             |
| **No hardcodear**              | Valores compartidos van en `app/constants/` (package, no archivo suelto) |
| **Detectores por dominio**     | Un archivo por detector, en el package de su área. NO monolito.         |
| **Orquestador por package**    | Cada área tiene su `detect_all.py` que une todos los detectores.         |

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

| Regla                   | Ejemplo                  |
| ----------------------- | ------------------------ |
| Funciones < 50 líneas   | ✅                       |
| Clases: PascalCase      | `DevConfig`              |
| Funciones: snake_case   | `process_excel`          |
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

| Archivo                                | Propósito                  | Estado |
| -------------------------------------- | -------------------------- | ------ |
| `app/services/exporter.py`             | Orquestador de exportación | ✅     |
| `app/services/cruce_sheet.py`          | Hoja CruceFacturas         | ✅     |
| `app/services/odontologia/detect_all.py`  | Detección odontología      | ✅     |
| `app/services/urgencias/detect_all.py`    | Detección urgencias        | ✅     |
| `app/services/equipos_basicos/detect_all.py` | Detección equipos básicos | ✅     |
| `app/utils/column_filter.py`           | Filtrado de columnas       | ✅     |
| `app/utils/formatting.py`              | Formato condicional        | ✅     |
| `app/services/excel_column_headers.py` | Lee headers Excel (Polars) | ✅     |
| `app/utils/input_data.py`              | Paths seguros              | ✅     |

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
