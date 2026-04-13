---
name: asis-hos-excel-headers
description: >
  Encabezados Excel del sistema de facturación médica EPS MALLAMAS.
  Trigger: Cuando se trabaja con archivos Excel - lectura, escritura, reglas, mapeo de columnas.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.1"
---

## CATÁLOGO COMPLETO DE ENCABEZADOS

> ⚠️ **IMPORTANTE**: Antes de crear cualquier regla o usar una columna, consulta este catálogo.
> Los nombres DEBEN ser exactos - el sistema no infiere coincidencias parciales.

---

## 📋 COLUMNAS USADAS EN REGLAS (contexto)

> Estas son las columnas que actualmente se usan en el sistema. **Antes de crear una nueva regla, usar estas.**

| # | Columna EXACTA | Qué es | Para qué sirve |
|---|----------------|--------|----------------|
| 1 | `Número Factura` | Número de factura | Identificador único de la factura que se revisa |
| 2 | `Vlr. Subsidiado` | Valor subsidiado | Valor del procedimiento (detectar decimales) |
| 3 | `Vlr. Procedimiento` | Valor del procedimiento | Valor del procedimiento (detectar decimales) |
| 4 | `Tipo Procedimiento` | **NOMBRE** del tipo de procedimiento | Detectar doble tipo (ej: "Consultas") |
| 5 | `Cód. Equivalente CUPS` | Código numérico del procedimiento | Identifica qué procedimiento es (antes era "Código") |
| 6 | `Procedimiento` | **NOMBRE** del procedimiento | Ruta duplicada, validación de convenio |
| 7 | `Nº Identificación` | Número de identificación del paciente | Identifica al paciente en todas las reglas |
| 8 | `Convenio Facturado` | Nombre del tipo de convenio | Validar que el convenio corresponda al procedimiento |
| 9 | `Cantidad` | Número de procedimientos realizados | Detectar cantidades anómalas |
| 10 | `Centro Costo` | Nombre de la agrupación del servicio | Validar centro de costo correcto |
| 11 | `Entidad Cobrar` | **NOMBRE** de la entidad (no el código) | Varias reglas de validación |
| 12 | `Tipo Identificación` | Tipo (CC, RC, TI, etc.) | Validar tipo ID vs edad del paciente |
| 13 | `Fec. Nacimiento` | Fecha de nacimiento del paciente | Validar tipo ID vs edad del paciente |
| 14 | `Fec. Factura` | Fecha de la factura | Validar ruta duplicada (mismo paciente, misma fecha) |
| 15 | `Profesional Atiende` | Nombre del profesional | Validar profesional correcto |
| 16 | `Código Tipo Procedimiento` | **CÓDIGO** del tipo (02=Diag, 14=Traslados) | Diferente del "Tipo Procedimiento" (nombre) |
| 17 | `Laboratorio` | Si es laboratorio (Sí/No) | Validar si es laboratorio |
| 18 | `Cód Entidad Cobrar` | **CÓDIGO** de la entidad (no el nombre) | Más preciso que "Entidad Cobrar" |
| 19 | `IDE Contrato` | Código del contrato (969, etc.) | Validar IDE Contrato correcto |
| 20 | `Entidad Afiliación` | Nombre completo de entidad de afiliación | Validar código entidad vs entidad afiliación |
| 21 | `Edad Completa` | Edad del paciente | Validar consistencia de datos |

---

### 📦 OTRAS COLUMNAS DISPONIBLES (no usadas aún)

> Estas columnas existen en el Excel pero no se usan en las reglas actuales.

| Columna EXACTA | Descripción |
|----------------|-------------|
| `Primer Apellido` | Primer apellido del paciente |
| `Segundo Apellido` | Segundo apellido |
| `Primer Nombre` | Primer nombre |
| `Segundo Nombre` | Segundo nombre |
| `Sexo` | Sexo del paciente |
| `Cita` | Fecha de cita |
| `Tipo Cita` | Tipo de cita |
| `Responsable Cierra Facturar` | Responsable que cierra la facturación |
| `Tipo Entidad Cobrar` | Tipo de entidad |
| `Cód. Tarifario` | Código tarifario |
| `Tarifario` | Nombre tarifario |
| `Nº Reingreso` | Número de reingreso |
| `Fecha Último Reingreso` | Fecha de último reingreso |
| `Nº Solicitud Laboratorio` | Número de solicitud de laboratorio |
| `Laboratorio Pendiente` | Laboratorio pendiente |
| `Vacuna` | Vacuna |
| `Vacuna Pendiente` | Vacuna pendiente |
| `ID` | ID del registro |
| `Alto Riesgo` | Indicador de alto riesgo |
| `LASA` | Indicador LASA |
| `CUM` | Código CUM |
| `Vlr. Copago` | Valor copago |
| `Concentración` | Concentración del medicamento |
| `Área Trabajo` | Área de trabajo |
| `Forma Farmacéutica` | Forma farmacéutica |
| `Principio Activo` | Principio activo |
| `Presentación Comercial` | Presentación comercial |
| `Unidad Medida` | Unidad de medida |
| `Fec. Procedimiento` | Fecha del procedimiento |
| `Identificación Profesional` | Identificación del profesional |
| `Código Profesional` | Código del profesional |
| `Responsable Abre Facturar` | Responsable que abre |
| `Responsable Última Modificación` | Última modificación |
| `Nombre Tipo Identificación` | Nombre del tipo de identificación |
| `Tipo Entidad Afiliación` | Tipo de entidad de afiliación |
| `Curso Vida` | Curso de vida |
| `Edad` | Edad |
| `Medidad Edad` | Medida de edad |
| `Cód. Tipo Usuario` | Código tipo usuario |
| `Tipo Usuario` | Tipo de usuario |
| `Grupo Sisbén IV` | Grupo Sisbén IV |
| `Discapacitado` | Indicador de discapacidad |
| `Descripción Discapacidad` | Descripción de discapacidad |
| `Código Etnia` | Código de etnia |
| `Etnia` | Etnia |
| `Código Grupo Indígena` | Código grupo indígena |
| `Grupo Indígena` | Grupo indígena |
| `Nombre Alterno` | Nombre alternativo |
| `Teléfono` | Teléfono |
| `Celular` | Celular |
| `Cód. Depto.` | Código de departamento |
| `Departamento` | Departamento |
| `Cód. Municipio` | Código de municipio |
| `Municipio` | Municipio |
| `Cód. Barrio` | Código de barrio |
| `Barrio` | Barrio |
| `Zona` | Zona |
| `Comuna` | Comuna |
| `Codigo` | Código |
| `Grupo Especial` | Grupo especial |
| `Victima Conflicto` | Víctima del conflicto |
| `RIPS` | RIPS |
| `Veces Consulta` | Veces en consulta |
| `Causa Externa` | Causa externa |
| `Nombre Causa Externa` | Nombre de causa externa |
| `Finalidad` | Finalidad |
| `Nombre Finalidad` | Nombre de finalidad |
| `Cód. Dx Ingreso` | Código diagnóstico ingreso |
| `Dx Ingreso` | Diagnóstico ingreso |
| `Cód. Dx Principal` | Código diagnóstico principal |
| `Dx Principal` | Diagnóstico principal |
| `Cód. Dx Relacionado 1` | Código diagnóstico relacionado 1 |
| `Dx Relacionado 1` | Diagnóstico relacionado 1 |
| `Cód. Dx Relacionado 2` | Código diagnóstico relacionado 2 |
| `Dx Relacionado 2` | Diagnóstico relacionado 2 |
| `Cód. Dx Relacionado 3` | Código diagnóstico relacionado 3 |
| `Dx Relacionado 3` | Diagnóstico relacionado 3 |
| `Diagnóstico Complicación` | Diagnóstico de complicación |
| `Dx Complicación` | Diagnóstico complicación |
| `Diagnóstico Causa Muerte` | Diagnóstico causa muerte |
| `Dx Causa Muerte` | Diagnóstico causa muerte |
| `Diagnóstico Muerte Madre` | Diagnóstico muerte madre |
| `Dx Muerte Madre` | Diagnóstico muerte madre |
| `Cód. Forma Quirúrgica` | Código forma quirúrgica |
| `Forma Quirúrgica` | Forma quirúrgica |
| `Cód. Tipo Servicio` | Código tipo servicio |
| `Tipo Servicio` | Tipo de servicio |
| `RIPS Pendiente` | RIPS pendiente |
| `Reporta Rips` | Reporta RIPS |
| `Tipo Factura Descripción` | Tipo de factura (Intramural, etc.) |
| `Zona` | Zona |
| `Comuna` | Comuna |
| `Codigo` | Código |
| `Grupo Especial` | Grupo especial |
| `Victima Conflicto` | Víctima del conflicto |
| `RIPS` | RIPS |
| `Veces Consulta` | Veces en consulta |
| `Causa Externa` | Causa externa |
| `Nombre Causa Externa` | Nombre de causa externa |
| `Finalidad` | Finalidad |
| `Nombre Finalidad` | Nombre de finalidad |
| `Cód. Dx Ingreso` | Código diagnóstico ingreso |
| `Dx Ingreso` | Diagnóstico ingreso |
| `Cód. Dx Principal` | Código diagnóstico principal |
| `Dx Principal` | Diagnóstico principal |
| `Cód. Dx Relacionado 1` | Código diagnóstico relacionado 1 |
| `Dx Relacionado 1` | Diagnóstico relacionado 1 |
| `Cód. Dx Relacionado 2` | Código diagnóstico relacionado 2 |
| `Dx Relacionado 2` | Diagnóstico relacionado 2 |
| `Cód. Dx Relacionado 3` | Código diagnóstico relacionado 3 |
| `Dx Relacionado 3` | Diagnóstico relacionado 3 |
| `Diagnóstico Complicación` | Diagnóstico de complicación |
| `Dx Complicación` | Diagnóstico complicación |
| `Diagnóstico Causa Muerte` | Diagnóstico causa muerte |
| `Dx Causa Muerte` | Diagnóstico causa muerte |
| `Diagnóstico Muerte Madre` | Diagnóstico muerte madre |
| `Dx Muerte Madre` | Diagnóstico muerte madre |
| `Cód. Forma Quirúrgica` | Código forma quirúrgica |
| `Forma Quirúrgica` | Forma quirúrgica |
| `Cód. Tipo Servicio` | Código tipo servicio |
| `Tipo Servicio` | Tipo de servicio |
| `RIPS Pendiente` | RIPS pendiente |
| `Reporta Rips` | Reporta RIPS |

---

## Nombres internos (en código Python)

| Nombre interno | Nombre EXACTO en Excel |
|----------------|------------------------|
| `numero_factura` | "Número Factura" |
| `vlr_subsidiado` | "Vlr. Subsidiado" |
| `vlr_procedimiento` | "Vlr. Procedimiento" |
| `codigo_tipo_procedimiento` | "Código Tipo Procedimiento" |
| `tipo_procedimiento` | "Tipo Procedimiento" |
| `codigo` | "Cód. Equivalente CUPS" |
| `procedimiento` | "Procedimiento" |
| `identificacion` | "Nº Identificación" |
| `convenio_facturado` | "Convenio Facturado" |
| `cantidad` | "Cantidad" |
| `laboratorio` | "Laboratorio" |
| `centro_costo` | "Centro Costo" |
| `codigo_entidad_cobrar` | "Cód Entidad Cobrar" |
| `entidad_cobrar` | "Entidad Cobrar" |
| `entidad_afiliacion` | "Entidad Afiliación" |
| `tipo_factura_descripcion` | "Tipo Factura Descripción" |
| `ide_contrato` | "IDE Contrato" |
| `tipo_identificacion` | "Tipo Identificación" |
| `fec_nacimiento` | "Fec. Nacimiento" |
| `fec_factura` | "Fec. Factura" |
| `profesional_identificacion` | "Identificación Profesional" |
| `profesional_atiende` | "Profesional Atiende" |
| `edad_completa` | "Edad Completa" |

---

## When to Use

Usar esta skill cuando:
- Se leen encabezados de archivos Excel del sistema
- Se mapean columnas entre diferentes hojas o archivos
- **Se agregan nuevas reglas que usan columnas del Excel** ← IMPORTANTE
- Se modifican los headers en constants.py

---

## Critical Patterns

### ⚠️ REGLA DE ORO: Nombres únicos y no ambiguos

**PROBLEMA**: "Código" es ambiguo — puede significar:
- Código del procedimiento
- Código Tipo Procedimiento
- Código Entidad Cobrar

**SOLUCIÓN**: Usar nombres completos y específicos del catálogo.

### ⚠️ ANTES DE CREAR UNA REGLA

1. **Consultar este catálogo** - verificar que la columna existe
2. **Usar el nombre EXACTO** - sin variaciones
3. **Verificar el tipo de Excel** - algunas columnas solo existen en Urgencias

---

## Anti-Patrones (NO HACER)

```python
# ❌ NO usar "Código" sin especificar - es ambiguo
codigo = sheet["Código"].value  # Puede ser cualquier código

# ✅ Especificar según el contexto
codigo_procedimiento = "Código"  # Código del procedimiento
codigo_tipo = "Código Tipo Procedimiento"  # Tipo (02, 14)
codigo_entidad = "Cód Entidad Cobrar"  # Código de entidad
```

```python
# ❌ Asumir que una columna existe en todos los Excel
# Las columnas de Urgencias NO existen en Odontología

# ✅ Verificar existencia antes de usar
if "Código Tipo Procedimiento" in headers:
    # usar lógica de urgencias
```

---

## Ubicación de los mapeos

El mapeo de columnas está en:
- `app/services/revision_sheet.py` → `_get_column_indices()` (líneas ~185-276)
- `app/services/transversales/estructura_excel.py` → `EXPECTED_HEADERS_LIMPIO` (líneas ~23-156)

**Para agregar nuevas columnas**:
1. Verificar que existe en este catálogo
2. Agregar el nombre EXACTO del Excel en `constants.py` si es una constante
3. Agregar el mapeo en `_get_column_indices` de `revision_sheet.py`
4. Agregar la columna a `COLUMNS_TO_KEEP` o `URGENCIA_COLUMNS_TO_KEEP` si debe mostrarse

---

## Commands

```bash
# Ver encabezados actuales del sistema
python3 -c "from app.services.excel_column_headers import get_excel_column_headers; print(get_excel_column_headers('app/data/input/tu_archivo.xlsx'))"

# Ver mapeos en constants.py
grep -E "(COLUMNS|CODIGO|URGENCIA)" app/constants.py
```

---

## Resources

- **Archivo de reglas**: `app/services/revision_sheet.py` - `_get_column_indices()`
- **Constantes**: `app/constants.py` - secciones COLUMNS, URGENCIAS
- **Headers esperados**: `app/services/transversales/estructura_excel.py` - `EXPECTED_HEADERS_LIMPIO`
- **Lectura de headers**: `app/services/excel_column_headers.py`