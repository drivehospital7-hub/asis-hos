---
name: asis-hos-excel-headers
description: >
  Convenciones de nomenclatura para encabezados Excel del sistema de facturación.
  Trigger: Cuando se trabaja con archivos Excel del proyecto (lectura, escritura, mapeo de columnas).
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

Usar esta skill cuando:
- Se leen encabezados de archivos Excel del sistema
- Se mapean columnas entre diferentes hojas o archivos
- Se agregan nuevas reglas que usan columnas del Excel
- Se modifican los headers en constants.py

---

## Critical Patterns

### ⚠️ REGLA DE ORO: Nombres únicos y no ambiguos

**PROBLEMA**: "Código" es ambiguo — puede significar:
- Código del procedimiento
- Código Tipo Procedimiento
- Código Entidad Cobrar

**SOLUCIÓN**: Usar nombres completos y específicos en el Excel fuente.

---

## Nombres oficiales de columnas (LEER del Excel)

Estos son los únicos nombres que deben existir en los archivos Excel de entrada:

### Columnas base (Odontología + Urgencias)

| Nombre exacto en Excel | Descripción |
|------------------------|-------------|
| `Número Factura` | Número de factura |
| `Vlr. Subsidiado` | Valor Subsidiado |
| `Vlr. Procedimiento` | Valor del procedimiento |
| `Tipo Procedimiento` | Tipo de procedimiento (Consultas, etc.) |
| `Procedimiento` | Nombre del procedimiento |
| `Nº Identificación` | Número de identificación del paciente |
| `Convenio Facturado` | Convenio (Asistencial / Promoción y Prevención) |
| `Cantidad` | Cantidad del procedimiento |
| `Centro Costo` | Centro de costo |
| `Entidad Cobrar` | Nombre de la entidad |
| `Tipo Identificación` | Tipo de identificación (CC, RC, TI, etc.) |
| `Fec. Nacimiento` | Fecha de nacimiento |
| `Fec. Factura` | Fecha de factura |
| `Profesional Atiende` | Nombre del profesional |
| `Primer Apellido` | Primer apellido del paciente |
| `Segundo Apellido` | Segundo apellido |
| `Primer Nombre` | Primer nombre |
| `Segundo Nombre` | Segundo nombre |
| `Sexo` | Sexo del paciente |
| `Cita` | Fecha de cita |
| `Tipo Cita` | Tipo de cita |
| `Responsable Cierra Facturar` | Responsable |

### Columnas exclusivas de Urgencias

| Nombre exacto en Excel | Descripción |
|------------------------|-------------|
| `Código Tipo Procedimiento` | Código del tipo (02=Diagnóstico, 14=Traslados) |
| `Laboratorio` | Si es laboratorio (Sí/No) |
| `Código` | **⚠️ Usar solo para procedimientos con nombre unambiguous** |
| `Cód Entidad Cobrar` | Código de la entidad (EPSI05, ESS118, etc.) |
| `Tipo Factura Descripción` | Tipo de factura (Intramural, etc.) |
| `IDE Contrato` | IDE del contrato |

---

## Nombres internos (en código Python)

Usar estos nombres en código + **coincidencia EXACTA** (sin variantes):

> ⚠️ **IMPORTANTE**: El código ya NO infiere nombres. Si el Excel no tiene el nombre exacto, reporta error en lugar de adivinar.

| Nombre interno | Nombre EXACTO en Excel |
|----------------|------------------------|
| `numero_factura` | "Número Factura" |
| `vlr_subsidiado` | "Vlr. Subsidiado" |
| `vlr_procedimiento` | "Vlr. Procedimiento" |
| `codigo_tipo_procedimiento` | "Código Tipo Procedimiento" |
| `tipo_procedimiento` | "Tipo Procedimiento" |
| `codigo` | "Código" |
| `procedimiento` | "Procedimiento" |
| `identificacion` | "Nº Identificación" |
| `convenio_facturado` | "Convenio Facturado" |
| `cantidad` | "Cantidad" |
| `laboratorio` | "Laboratorio" |
| `centro_costo` | "Centro Costo" |
| `codigo_entidad_cobrar` | "Cód Entidad Cobrar" |
| `entidad_cobrar` | "Entidad Cobrar" |
| `tipo_factura_descripcion` | "Tipo Factura Descripción" |
| `ide_contrato` | "IDE Contrato" |
| `tipo_identificacion` | "Tipo Identificación" |
| `fec_nacimiento` | "Fec. Nacimiento" |
| `fec_factura` | "Fec. Factura" |
| `profesional_identificacion` | "Identificación Profesional" |
| `profesional_atiende` | "Profesional Atiende" |

---

## Anti-Patrones (NO HACER)

```python
# ❌ NO usar "Código" sin especificar
# Puede significar código del procedimiento O código tipo procedimiento

# ✅ USAR nombres completos en constants.py
CODIGO_TIPO_PROCEDIMIENTO = "Código Tipo Procedimiento"  # Para tipo (02, 14)
CODIGO_PROCEDIMIENTO = "Código"  # Para código específico del procedimiento
CODIGO_ENTIDAD_COBRAR = "Cód Entidad Cobrar"  # Para código de entidad
```

```python
# ❌ Mapeo ambiguo en _get_column_indices
("codigo",): "codigo"  # NO: qué tipo de código?

# ✅ Mapeo específico
("código",): "codigo"  # Código del procedimiento
("código tipo procedimiento",): "codigo_tipo_procedimiento"  # Tipo de código
("cód entidad cobrar",): "codigo_entidad_cobrar"  # Código de entidad
```

---

## Ubicación de los mapeos

El mapeo de columnas está en:
- `app/services/revision_sheet.py` → `_get_column_indices()` (líneas ~157-203)
- `app/services/excel_column_headers.py` → función de lectura de headers

**Para agregar nuevas columnas**:
1. Agregar el nombre EXACTO del Excel en `constants.py` si es una constante
2. Agregar el mapeo en `_get_column_indices` de `revision_sheet.py`
3. Agregar la columna a `COLUMNS_TO_KEEP` o `URGENCIA_COLUMNS_TO_KEEP` si debe mostrarse

---

## Commands

```bash
# Ver encabezados actuales del sistema
python -c "from app.services.excel_column_headers import get_excel_column_headers; print(get_excel_column_headers('app/data/input/test_odontologia.xlsx'))"

# Ver mapeos en constants.py
cat app/constants.py | grep -E "(COLUMNS|CODIGO|URGENCIA)"
```

---

## Resources

- **Archivo de reglas**: `app/services/revision_sheet.py` - `_get_column_indices()`
- **Constantes**: `app/constants.py` - secciones COLUMNS, URGENCIAS
- **Lectura de headers**: `app/services/excel_column_headers.py`