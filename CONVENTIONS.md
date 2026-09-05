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

La validación solo marca error cuando el tipo de documento es **incompatible con la edad** del paciente. Tipos sin restricción de edad (PT, SC, PE, PAS, NIP, NIT) no se validan contra edad.

| Edad del paciente | Solo marcan error si el tipo es... |
|-------------------|------------------------------------|
| **< 7 años** | **TI**, **TE**, **CC**, **AS** (requieren 7+ o 18+) |
| **7 - 17 años** | **CC**, **AS**, **CE** (requieren 18+), **RC** (es para < 7) |
| **≥ 18 años** | **TI**, **TE**, **RC** (son para < 18), **MS** (es para < 18) |

#### Tipos con Validación Específica

| Tipo | Descripción | Condición de error |
|------|-------------|--------------------|
| **CN** | Certificado de Nacido Vivo | Solo válido si edad < 2 meses. Si ≥ 2 meses → 🔴 Error |
| **CE** | Cédula de Extranjería | Como CC: solo válido si edad ≥ 18 años. Si < 18 → 🔴 Error |
| **TE** | Tarjeta de Extranjería | Como TI: válido para 7-17 años. Si < 7 o ≥ 18 → 🔴 Error |
| **MS** | Menor sin Identificación | Solo válido si edad < 18 años. Si ≥ 18 → 🔴 Error |
| **AS** | Adulto sin Identificación | Solo válido si edad ≥ 18 años. Si < 18 → 🔴 Error |
| **RC** | Registro Civil | Válido para < 7 años |
| **TI** | Tarjeta de Identidad | Válido para 7-17 años |
| **CC** | Cédula de Ciudadanía | Válido para ≥ 18 años |

#### Tipos sin Restricción de Edad

Los siguientes tipos son válidos para cualquier edad:

| Tipo | Descripción |
|------|-------------|
| **PT** | Permiso de Protección Temporal |
| **SC** | Salvoconducto |
| **PE** | Permiso Especial |
| **PAS** | Pasaporte |
| **NIP** | Número de Identificación Personal |
| **NIT** | Número de Identificación Tributaria |

### 2. Decimales

| Condición | Columna afectada |
|-----------|------------------|
| `Vlr. Subsidiado` o `Vlr. Procedimiento` tiene decimales | Número Factura |

### 3. Entidad Cobrar vs Entidad Afiliación

Compara `Cód Entidad Cobrar` vs código extraído de `Entidad Afiliación` (formato: `... - {CODIGO} ...`).

| Condición | Resultado |
|-----------|-----------|
| Código en `Cód Entidad Cobrar` ≠ código en `Entidad Afiliación` | 🔴 Error |

### 4. Tipo Usuario

La columna `Tipo Usuario` solo puede contener los siguientes valores:

| Valor válido | Descripción |
|--------------|-------------|
| **SUBSIDIADO** | Régimen subsidiado |
| **CONTRIBUTIVO** | Régimen contributivo |
| **OTROS (REGÍMENES ESPECIALES, EOC)** | Regímenes especiales |
| **VINCULADO** | Usuarios vinculados |
| **PARTICULAR** | Usuarios particulares |

> Cualquier otro valor en `Tipo Usuario` → 🔴 Error

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
| **Cantidades (Urgencias)** | Códigos 05DSB01, 5DSB01, 890601, 890701, 129B02, 12333 en Urgencias deben tener cantidad ≤ 1 |
| **Cantidades (Hospitalización)** | Reglas especiales por código y estancia |
| **Sala de Observación / Hospitalización** | NO aplicAN si `Tarifario = "SOAT"` |

#### Centro de Costo — Urgencias

| Código CUPS | Tipo Factura | Centro de costo esperado |
|-------------|--------------|-------------------------|
| **890601** | Hospitalización | **HOSPITALIZACIÓN - ESTANCIA GENERAL** |
| **861101** | Cualquiera | **URGENCIAS** |

#### Cantidades — Hospitalización

| Código | Tipo Factura | Regla | Ejemplo |
|--------|--------------|-------|---------|
| **129B02** | Hospitalización | Cantidad = días_estancia + 1 | 12h → 1 día → cantidad 1; 26h (1d2h) → 2 días → cantidad 2 |
| **890601** | Hospitalización | Cantidad = días_redondeados_arriba; NO puede existir si < 24h | < 24h → ERROR; 35.5h → 2 días → cantidad 2 |

#### Cups equivalentes urgencias

| Código | Cód. Equivalente CUPS | Acción |
|--------|----------------------|--------|
| **890201** | **890201** | ERROR - Debe usarse **890701** o **12333** |
| **129B01** | **129B02** | ERROR - Debe usarse **129B02** |

#### Sala de Observación — Estancia >6h / ≤6h

**No SOAT:**

| Estancia | ESS118 / ESSC18 | Otras entidades |
|----------|-----------------|-----------------|
| **≤ 6 horas** | `5DSB01` | `5DSB01` |
| **> 6 horas** | `05DSB01` | `129B02` |

**SOAT:**

| Estancia | Código requerido |
|----------|-----------------|
| **≤ 6 horas** | `38915` |
| **> 6 horas** | `38114` |

> **Regla complementaria SOAT**: Si factura tiene código `38114` o `38915` y `Tipo Factura = Urgencias`, entonces debe tener también `39145` y `39131`.
> **Prohibido SOAT**: Si `Tarifario = SOAT` y `Tipo Factura = Urgencias` → NO puede tener código `39133`.
> **Prohibido SOAT Hospitalización**: Si `Tarifario = SOAT` y `Tipo Factura = Hospitalización` → NO puede tener códigos `39145` ni `38915`.
> **Obligatorio SOAT Hospitalización**: Si `Tarifario = SOAT` y `Tipo Factura = Hospitalización` → debe tener códigos `39133`, `38114` y `39131`.
> **Cantidades SOAT Urgencias**: Si `Tarifario = SOAT` y `Tipo Factura = Urgencias`, los códigos `39145`, `38114`, `38915`, `39131` deben tener cantidad = 1.
> **Cantidades SOAT Hospitalización**: Si `Tarifario = SOAT` y `Tipo Factura = Hospitalización`:
>   - Código `38114`: cantidad = días_estancia + 1 (ej: <24h → 1, 26h (1d2h) → 2, 50h (2d2h) → 3)
>   - Código `39131`: cantidad = días_estancia (ej: <24h → 0, 26h (1d2h) → 1, 50h (2d2h) → 2)

> **Menor a 2h**: No requiere código de sala de observación (tanto SOAT como no-SOAT)

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
| 110001, 110001AUX, 861101, 890403, 890406, 890409, 890412, 939403 | ESS118 | siempre | Cualquiera **EXCEPTO 969** |

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

### 📋 Abiertas Urgencias — Horarios y Responsables

Reglas del módulo de cronograma de turnos para asignación automática de responsable.

#### 30 minutos de recepción (handover)

El turno entrante se hace cargo **30 minutos antes** del cambio formal de horario.  
Esto aplica a los tres turnos:

| Turno | Horario formal | Responsable desde | Responsable hasta |
|-------|---------------|-------------------|-------------------|
| **Mañana** | 07:00 – 13:00 | 06:30 | 12:29 |
| **Tarde** | 13:00 – 19:00 | 12:30 | 18:29 |
| **Noche** | 19:00 – 07:00 | 18:30 | 06:29 |

Ejemplo: si el turno de tarde es de 1:00 PM a 7:00 PM, a las 6:30 PM el responsable
ya es el del turno de noche (no el de las 7:00 PM).

#### Almacenamiento por mes y gating `Sin horario`

Horarios en `app/data/horarios/abiertas_urgencias_YYYY-MM.json` (un archivo por mes, escritura atómica temp+rename, migración idempotente desde `app/data/horario_abiertas_urgencias.json` legacy). `GET /api/schedules` lista `YYYY-MM` ordenados, `GET/POST/DELETE /api/schedule?mes=&anio=` operan por mes (sin params = compat legacy `mes_actual`). Frontend resuelve `calcularResponsable(fechaCrea, fechaEgreso, horarioForMonth)` por `YYYY-MM(egreso)`: si `horarioForMonth` es `null`/vacío o `fechaEgreso` malformada → `"Sin horario"` (sentinel distinto de `Sin Egreso`/`Sin cronograma`/`Sin turno`), bloquea `Envío` con `getSinEgresoButtonConfig(..., isSinHorario=true)` → `Sin horario: cargue horario de ese mes` y `POST /api/control-errores` rechaza `Factura Abierta + Sin horario` con `[BACK][ERROR]`.

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
| C | Cups Equivalentes |
| D | MAL CAPITADO |
| E | Cantidades (códigos 05DSB01, 5DSB01, 890601, 890701, 129B02, 12333 con cantidad >1 en Tipo Factura = Urgencias) |
| F | Cantidades Hospitalización (códigos 129B02 y 890601 con cantidades incorrectas según estancia) |

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

*Última actualización: 2026-05-12*