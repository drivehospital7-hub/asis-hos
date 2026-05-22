---
name: asis-hos-detector-pattern
description: >
  Patrón para crear detectores de problemas en Excels de facturación médica EPS MALLAMAS.
  Trigger: Crear, modificar o extender detectores de validación de facturas, reglas de negocio, o funciones en services/*/detect_all.py.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## PATRÓN DE DETECTOR

> ⚠️ **LEER COMPLETO antes de crear o modificar cualquier detector.**

Cada detector es una función `detect_<algo>(data_sheet, indices) -> list[dict]` que vive en el package de su área y encuentra UN tipo de problema.

---

## 📁 DÓNDE VIVE CADA DETECTOR

| Área | Package | Orquestador |
|------|---------|-------------|
| Compartido (varias áreas) | `app/services/transversales/` | `detect_all.py` del área que lo invoca |
| Odontología | `app/services/odontologia/` | `app/services/odontologia/detect_all.py` |
| Urgencias | `app/services/urgencias/` | `app/services/urgencias/detect_all.py` |
| Equipos Básicos | `app/services/equipos_basicos/` | `app/services/equipos_basicos/detect_all.py` |

### Reglas de ubicación
- **Si la regla aplica a todas las áreas** → `transversales/` (parametrizada con thresholds)
- **Si la regla es exclusiva de un área** → package de esa área
- **NO mezclar** reglas de distintas áreas en el mismo archivo
- **NO crear detectores en routes/ o utils/**

---

## 🏗️ CONTRATO DEL DETECTOR

```python
from openpyxl.worksheet.worksheet import Worksheet

def detect_mi_problema(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    # parámetros opcionales con valor por defecto
    umbral: int = 10,
) -> list[dict]:
    """Detecta [BREVE DESCRIPCIÓN DEL PROBLEMA].

    Args:
        data_sheet: Hoja activa del Excel (openpyxl).
        indices: Mapeo de nombre_columna -> índice 0-based (o None si falta).

    Returns:
        Lista de dicts con {"factura": str, "problema": str, ...}
        Vacía si no hay problemas o si faltan columnas necesarias.
    """
    resultado: list[dict] = []

    # 1. Validar columnas necesarias
    num_fact_idx = indices.get("numero_factura")
    mi_columna_idx = indices.get("mi_columna")
    if None in (num_fact_idx, mi_columna_idx):
        return []

    # 2. Recorrer filas (openpyxl es 1-based, saltar header en fila 1)
    for row in range(2, data_sheet.max_row + 1):
        factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        valor = data_sheet.cell(row=row, column=mi_columna_idx + 1).value

        if not factura or valor is None:
            continue

        # 3. Lógica de detección
        if es_problema(valor, umbral):
            resultado.append({
                "factura": str(factura).strip(),
                "problema": f"Descripción del problema: {valor}",
            })

    return resultado
```

---

## ✅ CHECKLIST PARA CREAR UN DETECTOR NUEVO

Antes de escribir código, verificar:

- [ ] **¿Existe ya en transversales/ un detector genérico que pueda reutilizar?** (ruta_duplicada, cantidades_anomalas, decimales, tipo_documento_edad, etc.)
- [ ] **¿La columna que necesito existe?** Consultar skill `asis-hos-excel-headers` primero
- [ ] **¿Va en el package correcto?** (transversales/ si es compartido, área/ si es exclusivo)
- [ ] **¿El nombre de la función sigue el patrón?** `detect_<verbo>_<area>`
- [ ] **¿Tiene la signature correcta?** `(data_sheet: Worksheet, indices: dict[str, int | None]) -> list[dict]`
- [ ] **¿Maneja columnas faltantes?** Si `indices["columna"] is None`, retornar `[]`
- [ ] **¿Tiene tests?** Crear `tests/services/test_<area>_<detector>.py`
- [ ] **¿Se registró en el orquestador?** Agregar llamado en `detect_all.py` del área

---

## 📊 FORMATO DE SALIDA

Cada detector retorna una lista de problemas. Cada problema es un dict:

```python
{
    "factura": "F001",         # Número de factura (SIEMPRE string)
    "problema": "Descripción",  # Texto legible del problema encontrado
    # Opcionales según el detector:
    "identificacion": "12345",
    "cantidad": 3,
    "tipo_procedimiento": "Consultas",
    "convenio": "PyP",
}
```

---

## 🔌 CÓMO REGISTRARLO EN EL ORQUESTADOR

En el `detect_all.py` del área correspondiente:

```python
from app.services.transversales.mi_regla import detect_mi_problema
from app.services.odontologia.mi_regla_odontologia import detect_mi_problema_odontologia

def detect_all_problems_odontologia(data_sheet, indices):
    problemas = []
    
    # Detectores transversales
    problemas.extend(detect_decimales(data_sheet, indices))
    problemas.extend(detect_tipo_documento_edad(data_sheet, indices))
    
    # Detectores propios del área
    problemas.extend(detect_mi_problema_odontologia(data_sheet, indices))
    
    return {
        "problemas": problemas,
        "totales": {"problemas": len(problemas)},
        "area": "odontologia",
    }
```

---

## 📚 EJEMPLOS EXISTENTES EN EL PROYECTO

| Archivo | Función | Líneas |
|---------|---------|--------|
| `app/services/transversales/decimales.py` | `detect_decimales()` | ~40 |
| `app/services/transversales/ruta_duplicada.py` | `detect_ruta_duplicada(threshold=3)` | ~50 |
| `app/services/transversales/cantidades_anomalas.py` | `detect_cantidades_anomalas()` | ~70 |
| `app/services/odontologia/profesionales.py` | `detect_profesionales_odontologia()` | ~30 |
| `app/services/urgencias/centro_costo_urgencias.py` | `detect_centro_costo_urgencias()` | ~45 |

---

## ⛔ ANTI-PATRONES

```python
# ❌ Detector que hace DOS cosas
def detect_problemas_mixtos(data_sheet, indices):
    # valida decimales
    # valida profesionales  ← NO: otro detector
    ...

# ✅ Cada cosa en su detector
problemas_decimales = detect_decimales(data_sheet, indices)
problemas_profesionales = detect_profesionales(data_sheet, indices)
```

```python
# ❌ Lógica en el orquestador (detect_all.py)
def detect_all(data_sheet, indices):
    problemas = []
    for row in range(2, data_sheet.max_row + 1):  # ← NO: va en un detector
        ...

# ✅ Orquestador SOLO llama detectores
def detect_all(data_sheet, indices):
    return {
        "problemas": (
            detect_uno(data_sheet, indices)
            + detect_dos(data_sheet, indices)
        ),
    }
```

```python
# ❌ Función de +100 líneas
# Partir en detectores más chicos o helpers internos
```

---

## 🔗 REFERENCIAS

- **Headers de columnas**: skill `asis-hos-excel-headers`
- **Reglas de negocio**: `CONVENTIONS.md`
- **Tests existentes**: `tests/services/test_<area>_<detector>.py`
- **Constantes por área**: `app/constants/<area>.py`
