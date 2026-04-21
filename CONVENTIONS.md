# Convenciones de Negocio — Control System

> **Versión**: 2.3.0  
> **Propósito**: Reglas de DOMINIO — validaciones, procedimientos, formatos específicos del negocio.  
> Para reglas técnicas (arquitectura, código) ver `AGENTS.md`.

---

## Dominio

**Sistema de Control de Facturación Médica** para EPS indígena MALLAMAS.

Áreas del sistema:
- **Odontología** — área principal
- **Urgencias** — códigos de urgencia con IDE Contrato
- **Equipos Básicos** — extensión de Odontología

---

## Reglas Transversales

> Aplican a **TODAS las áreas** (Odontología, Urgencias, Equipos Básicos)

### 1. Tipo de Identificación vs Edad

| Edad del paciente | Tipo esperado | Si no coincide |
|-------------------|---------------|----------------|
| **< 7 años** | **RC** (Registro Civil) | 🔴 Error |
| **7 - 17 años** | **TI** (Tarjeta de Identidad) | 🔴 Error |
| **≥ 18 años** | **CC** (Cédula de Ciudadanía) | 🔴 Error |
| **< 2 meses** | **CN** (Certificado de Nacimiento) | 🔴 Error |

Casos especiales (menores sin registro):
- < 18 años sin RC/TI → **MS** (Menor sin Identificación)
- ≥ 18 años sin CC → **AS** (Adulto sin Identificación)

#### Tipos de Documento No Válidos

Los siguientes tipos de documento NO están permitidos y deben marcarse como error:

| Tipo | Descripción |
|------|-------------|
| **CN** | Solo válido si edad < 2 meses (ver regla arriba) |
| **CE** | Cédula de Extranjería — no válido para este sistema |
| **NIP** | Número de Identificación Personal — no válido |
| **NIT** | Número de Identificación Tributaria — no válido |
| **PAS** | Pasaporte — no válido |
| **PE** | Permiso Especial — no válido |
| **SC** | Salvoconducto — no válido |

> **Nota**: Esta validación está implementada en el formato condicional (color rojo en la hoja de datos) pero NO se escribe en la hoja Revision.

### 2. Decimales

| Condición | Columna afectada |
|-----------|------------------|
| `Vlr. Subsidiado` o `Vlr. Procedimiento` tiene decimales | Número Factura |

### 3. Entidad Cobrar vs Entidad Afiliación

Compara `Cód Entidad Cobrar` vs código extraído de `Entidad Afiliación` (formato: `... - {CODIGO} ...`).

| Condición | Resultado |
|-----------|-----------|
| Código en `Cód Entidad Cobrar` ≠ código en `Entidad Afiliación` | 🔴 Error |

---

## Reglas por Área

### 🦷 Odontología

| Validación | Condición | Columna afectada |
|------------|-----------|------------------|
| **Doble tipo** | Factura con >1 tipo de procedimiento | Número Factura |
| **Ruta duplicada** | Paciente con ≥3 facturas en convenio PyP | Nº Identificación |
| **Convenio incorrecto** | Procedimiento PyP en convenio Asistencial (o viceversa) | Número Factura |
| **Cantidades anómalas** | Consultas ≥2, cantidad >10, PyP ≥3 | Número Factura |

#### Detalle de Cantidades

| Condición | Se marca como anómalo |
|-----------|----------------------|
| Tipo Procedimiento = "Consultas" AND Cantidad ≥ 2 | ✅ |
| Cantidad > 10 (cualquier tipo) | ✅ |
| Convenio = "Promoción y Prevención" AND Cantidad ≥ 3 | ✅ |

#### Procedimientos PyP (Promoción y Prevención) — CÓDIGOS CUPS

La validación se hace por **código CUPS** (columna "Código"), NO por nombre de procedimiento.

| Código CUPS | Procedimiento |
|-----------|-------------|
| **890203** | Consulta de Primera vez por Odontologia General |
| **997002** | Control de Placa Bacteriana |
| **997106** | Topicacion de Fluor en Barniz |
| **997107** | Aplicación de Sellantes |
| **997301** | Detartraje Supragingival |

##### Regla de Convenio Incorrecto

| Convenio | Código CUPS | Resultado |
|----------|-----------|-----------|
| Asistencial | Código de la lista PyP | ❌ Error |
| Promoción y Prevención | Código NO en lista PyP | ❌ Error |
| Asistencial | Código NO PyP | ✅ Ok |
| Promoción y Prevención | Código PyP | ✅ Ok |

---

### 🚨 Urgencias

| Validación | Descripción |
|------------|-------------|
| **Centros de costo** | Detecta códigos NO encontrados en DB para ESS118 + Regla 890601H |
| **IDE Contrato** | Por código + entidad (EPSI05, EPSIC5, ESS118, ESSC18, EPS037, EPSS41) |

#### Centro de Costo — Urgencias

| Código CUPS | Tipo Factura | Centro de costo esperado |
|-------------|--------------|-------------------------|
| **890601** | Hospitalización | **HOSPITALIZACIÓN - ESTANCIA GENERAL** |
| **890408** | Cualquiera | **URGENCIAS** |
| **861101** | Cualquiera | **URGENCIAS** |

#### Cups equivalentes urgencias

| Código | Cód. Equivalente CUPS | Acción |
|--------|----------------------|--------|
| **890201** | **890201** | ERROR - Debe usarse **890701** |

#### IDE Contrato — Urgencias

| Código | Entidad | Condición | IDE Contrato esperado |
|--------|---------|----------|------------------------|
| **906340** | EPSI05 | siempre | **986** |
| **861801** | EPSI05 | siempre | **977** |
| **890405** | EPSI05 | si tiene código 861801 en identificación | **976** |
| **890405** | EPSI05 | si NO tiene código 861801 | **977** |
| **861801** | EPSIC5 | siempre | **979** |
| **890405** | EPSIC5 | si tiene código 861801 en identificación | **967** |
| **890405** | EPSIC5 | si NO tiene código 861801 | **979** |

##### ESS118 (Centro de Costo)

| Código | Entidad | Condición | IDE Contrato esperado |
|--------|---------|----------|------------------------|
| 110001, 110001AUX, 861101, 890403, 890406, 890408, 890409, 890412, 939403 | ESS118 | siempre | Cualquiera **EXCEPTO 969** |

##### ESS118 (Código NO en DB)

| Campo | Condición | Acción |
|-------|-----------|--------|
| Entidad | = ESS118 | ✓ Requerido |
| IDE Contrato | = 969 | ✓ Requerido |
| Código CUPS | NO existe en `procedimientos.db` | → **ERROR** |
| Código Tipo Procedimiento | IN (09, 12, 13) | → **EXCLUIR** (no reportar) |

> **Ejemplo de error**: Factura con entidad ESS118, IDE=969, código CUPS "890403" que no existe en la DB → Reportar como error "CÓDIGO NO EN DB"

> **Nota**: EPSIC5 es una entidad DIFERENTE de EPSI05. No confundir.

##### ESS118 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| ESS118 | Código PyP (890203, 997002, 997106, 997107, 997301) | **970** o **974** |
| ESS118 | Código NO PyP | **969** o **973** |

##### ESSC18 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| ESSC18 | Código PyP (890203, 997002, 997106, 997107, 997301) | **975** |
| ESSC18 | Código NO PyP | **968** |

##### EPSS41 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| EPSS41 | Código PyP (890203, 997002, 997106, 997107, 997301) | **955** o **958** |
| EPSS41 | Código NO PyP | **956** o **959** |

##### EPS037 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| EPS037 | Código PyP (890203, 997002, 997106, 997107, 997301) | **961** |
| EPS037 | Código NO PyP | **962** |

##### EPSI05 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| EPSI05 | Código PyP (890203, 997002, 997106, 997107, 997301) | **977** |
| EPSI05 | Código NO PyP | **976** o **978** |

##### EPSIC5 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| EPSIC5 | Código PyP (890203, 997002, 997106, 997107, 997301) | **979** |
| EPSIC5 | Código NO PyP | **967** |

##### RES001 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| RES001 | Código PyP (890203, 997002, 997106, 997107, 997301) | **954** |
| RES001 | Código NO PyP | **953** |

##### ESS062 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| ESS062 | Código PyP (890203, 997002, 997106, 997107, 997301) | **922** |
| ESS062 | Código NO PyP | **921** |

##### ESSC62 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| ESSC62 | Código PyP (890203, 997002, 997106, 997107, 997301) | **863** |
| ESSC62 | Código NO PyP | **862** |

##### 0001 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| 0001 | Código PyP (890203, 997002, 997106, 997107, 997301) | **17** |
| 0001 | Código NO PyP | **984** |

##### EPSS005 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| EPSS005 | Código PyP (890203, 997002, 997106, 997107, 997301) | **933** |
| EPSS005 | Código NO PyP | **934** |

##### EPSC005 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| EPSC005 | Código PyP (890203, 997002, 997106, 997107, 997301) | **932** |
| EPSC005 | Código NO PyP | **931** |

##### 86 + Procedimientos NO PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| 86 | Código NO PyP | **911** |
| 86 | Código PyP | No aplica |

##### 86000 + Procedimientos PyP → IDE Contrato

| Entidad | Código CUPS | IDE Contrato esperado |
|--------|-----------|---------------------|
| 86000 | Código PyP (890203, 997002, 997106, 997107, 997301) | **920** |
| 86000 | Código NO PyP | **919** |

---

### 🔧 Equipos Básicos

Comparte las validaciones de Odontología:
- Doble tipo procedimiento
- Ruta duplicada (≥3 facturas PyP)
- Convenio incorrecto
- Cantidades anómalas

---

## Formato Condicional (Colores Excel)

### Hoja de Datos Principal

| Condición | Color | Código |
|-----------|-------|--------|
| MALLAMAS + Asistencial + ODONTOLOGIA | Rojo | `FF0000` |
| Tipo identificación no coincide con edad | Rojo | `FF0000` |

### Hoja CruceFacturas

| Columna | Significado | Color | Código |
|---------|-------------|-------|--------|
| B | Facturas Ok | Verde | `92D050` |
| D | Facturas Pendientes | Amarillo | `FFC000` |
| F | PDFs de Facturas | Rojo | `FF0000` |

### Hoja Revision — Odontología

Columnas sin color, solo listado de facturas problemáticas:

| Columna | Contenido |
|---------|-----------|
| A | Decimales |
| B | Doble tipo procedimiento |
| C | Ruta Duplicada |
| D | Convenio de procedimiento |
| E | Cantidades |

### Hoja Revision — Urgencias

| Columna | Contenido |
|---------|-----------|
| A | Centros de Costos |
| B | IDE Contrato |

---

## Columnas Relevantes

### Columnas que se muestran (las demás se ocultan)

```
Entidad Cobrar
Profesional Atiende
Fec. Factura
Número Factura
Tipo Entidad Cobrar
Convenio Facturado
Procedimiento
Tipo Identificación
Edad Completa
Nº Identificación
Primer Apellido
Segundo Apellido
Primer Nombre
Segundo Nombre
Sexo
Fec. Nacimiento
Responsable Cierra Facturar
Vlr. Procedimiento
Vlr. Subsidiado
Cantidad
Cita
Tipo Cita
Centro Costo
```

### Columnas clave para validaciones

| Columna | Uso |
|---------|-----|
| `Número Factura` | Identificador único |
| `Vlr. Subsidiado` | Detección de decimales |
| `Vlr. Procedimiento` | Detección de decimales |
| `Tipo Procedimiento` | Doble tipo, cantidades |
| `Convenio Facturado` | Convenio incorrecto, ruta duplicada |
| `Procedimiento` | Convenio incorrecto |
| `Nº Identificación` | Ruta duplicada |
| `Tipo Identificación` | Validación vs edad |
| `Fec. Nacimiento` | Cálculo de edad |
| `Fec. Factura` | Cálculo de edad al momento de factura |
| `Cantidad` | Cantidades anómalas |
| `Cód Entidad Cobrar` | Entidad Cobrar vs Entidad Afiliación |
| `Entidad Afiliación` | Entidad Cobrar vs Entidad Afiliación |

---

## Hojas del Excel de Salida

| Hoja | Propósito |
|------|-----------|
| **(activa)** | Datos filtrados con columnas visibles |
| **CruceFacturas** | Cruce: Ok (B), Pendientes (D), PDFs (F) |
| **Revision** | Facturas con problemas por categoría |

---

## Entidades

| Entidad | Valor esperado |
|---------|----------------|
| EPS | MALLAMAS EPS INDIGENA |
| Centro de costo | ODONTOLOGIA |
| Convenios válidos | Asistencial, Promoción y Prevención |

---

## Glosario

| Término | Significado |
|---------|-------------|
| PyP | Promoción y Prevención |
| RC | Registro Civil (< 7 años) |
| TI | Tarjeta de Identidad (7-17 años) |
| CC | Cédula de Ciudadanía (≥ 18 años) |
| MS | Menor sin Identificación |
| AS | Adulto sin Identificación |
| Ruta duplicada | Paciente con múltiples facturas PyP |

---

*Última actualización: 2026-04-13*