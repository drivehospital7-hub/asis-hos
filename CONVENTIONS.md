# Convenciones de Negocio — Control System

> **Versión**: 2.1.0  
> **Propósito**: Reglas de DOMINIO — validaciones, procedimientos, formatos específicos del negocio.  
> Para reglas técnicas (arquitectura, código) ver `AGENTS.md`.

---

## Dominio

**Sistema de Control de Facturación Médica** para EPS indígena MALLAMAS.

Área principal: **Odontología**

---

## Validaciones de Facturación

### Reglas de Detección de Problemas

| Validación | Condición | Columna afectada |
|------------|-----------|------------------|
| **Decimales** | `Vlr. Subsidiado` o `Vlr. Procedimiento` tiene decimales | Número Factura |
| **Doble tipo** | Factura con >1 tipo de procedimiento | Número Factura |
| **Ruta duplicada** | Paciente con ≥3 facturas en convenio PyP | Nº Identificación |
| **Convenio incorrecto** | Procedimiento PyP en convenio Asistencial (o viceversa) | Número Factura |
| **Cantidades anómalas** | Consultas ≥2, cantidad >10, PyP ≥3 | Número Factura |

### Detalle de Cantidades

| Condición | Se marca como anómalo |
|-----------|----------------------|
| Tipo Procedimiento = "Consultas" AND Cantidad ≥ 2 | ✅ |
| Cantidad > 10 (cualquier tipo) | ✅ |
| Convenio = "Promoción y Prevención" AND Cantidad ≥ 3 | ✅ |

---

## Procedimientos PyP (Promoción y Prevención)

Estos procedimientos DEBEN estar en convenio "Promoción y Prevención":

```
- Control de Placa Bacteriana
- Aplicación de Sellantes
- Detartraje Supragingival
- Topicacion de Fluor en Barniz
- Consulta de Primera vez por Odontologia General
```

### Regla de Convenio Incorrecto

| Convenio | Procedimiento | Resultado |
|----------|---------------|-----------|
| Asistencial | Procedimiento PyP (lista arriba) | ❌ Error |
| Promoción y Prevención | Procedimiento NO en lista PyP | ❌ Error |
| Asistencial | Procedimiento NO PyP | ✅ Ok |
| Promoción y Prevención | Procedimiento PyP | ✅ Ok |

---

## Tipo de Identificación vs Edad

| Edad del paciente | Tipo esperado | Si no coincide |
|-------------------|---------------|----------------|
| < 7 años | RC (Registro Civil) | 🔴 Rojo |
| 7 - 17 años | TI (Tarjeta de Identidad) | 🔴 Rojo |
| ≥ 18 años | CC (Cédula de Ciudadanía) | 🔴 Rojo |

Casos especiales (menores sin registro):
- < 18 años sin RC/TI → MS (Menor sin Identificación)
- ≥ 18 años sin CC → AS (Adulto sin Identificación)

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

### Hoja Revision

Columnas sin color, solo listado de facturas problemáticas:

| Columna | Contenido |
|---------|-----------|
| A | Decimales |
| B | Doble tipo procedimiento |
| C | Ruta Duplicada |
| D | Convenio de procedimiento |
| E | Cantidades |

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

*Última actualización: 2026-04-03*
