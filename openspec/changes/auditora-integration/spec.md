# Auditoría PDF (pdf-audit) — Especificación completa

## Propósito

Permitir que auditores ingresen una ruta de carpeta local al servidor y obtengan, en una sola interacción sincrónica, el análisis completo de todos los expedientes PDF dentro de ella: extracción y parseo de FEV, PDE y soportes, normalización y comparación FEV↔PDE, y validación de soportes contra reglas JSON. El resultado se muestra en un árbol expandible en el frontend React.

## Requisitos

### R1: Procesamiento sincrónico de carpeta

`POST /derechos/auditoria/procesar` DEBE aceptar `{"ruta": "string"}` y ejecutar `recorrer_carpeta(ruta)` de forma bloqueante. DEBE retornar la estructura resultante dentro del envelope `{"status", "data", "errors"}`. El campo `data` DEBE contener `ruta`, `estructura` (árbol anidado de expedientes), `total_expedientes` y `total_pdfs`.

| Escenario | Given | When | Then |
|-----------|-------|------|------|
| Happy path — carpeta con FEV + PDE + soportes | carpeta con `FEV_123.PDF`, `PDE.PDF`, `EPI_001.PDF` en subdirectorios | POST con `{"ruta": "..."}` | status=success, data.estructura tiene 1 expediente con 3 archivos y validaciones |
| Carpeta sin PDFs | carpeta vacía o solo con .txt | POST procesa | status=success, data.estructura={}, mensaje aclara que no hay PDFs |
| Ruta inexistente | ruta que no existe en el sistema de archivos | POST valida entrada | status=error + errors[0] describe el problema + HTTP 400 |
| Ruta sin permiso | subdirectorio sin permisos de lectura | walk encuentra el error | ese subdirectorio se omite, se loguea warning, no se corta el batch |

### R2: Interfaz de usuario

`GET /derechos/auditoria` DEBE renderizar `react_shell.html` con el entry point de Vite para la página de auditoría. La UI DEBE tener un campo de texto para la ruta, un botón "Procesar", y un árbol expandible de resultados. Los estados de carga, error y vacío DEBEN tener representación visual.

| Escenario | Given | When | Then |
|-----------|-------|------|------|
| Render inicial | usuario navega a `/derechos/auditoria` | GET | página carga sin errores JS, muestra input de ruta |
| Error de red | POST falla por timeout o servidor | fetch rechaza | UI muestra error claro, botón se rehabilita |
| Resultados vacíos | POST retorna estructura vacía | UI recibe data | se muestra "No se encontraron expedientes" |

### R3: Aislamiento de errores por PDF

Un PDF que no se pueda procesar NO DEBE cancelar el batch completo. Cada archivo DEBE envolverse en try/except. Si falla, DEBE incluirse en el resultado con `"error": "mensaje"` y el procesamiento continúa con el siguiente PDF.

| Escenario | Given | When | Then |
|-----------|-------|------|------|
| PDF corrupto | un PDF no se puede leer con fitz | se procesa ese archivo | se captura excepción, se agrega al resultado con campo error, resto del batch continúa |
| PDF con contraseña | PDF protegido que fitz no puede abrir | se intenta abrir | mismo comportamiento: error capturado, batch sigue |
| Layout FEV atípico | FEV con estructura de tabla diferente | parsear_fev retorna datos incompletos | no se lanza excepción; datos parciales se retornan con lo que se pudo extraer |

### R4: Respuesta estructurada

La respuesta DEBE seguir el formato canónico del sistema. El campo `data.estructura` DEBE ser un árbol de expedientes donde cada hoja contiene: `archivos` (lista con `tipo`, `archivo`, `data`), `validacion` (FEV normalizado + PDE normalizado + diferencias), `validacion_soportes` (resultados por soporte), `alerta_archivos` (PDE huérfano, FEV sin PDE), y `duplicado_global` (misma carpeta en múltiples ubicaciones).

| Escenario | Given | When | Then |
|-----------|-------|------|------|
| FEV sin PDE | carpeta con FEV pero sin PDE | validación post-proceso | alerta_archivos.mensaje = "NO EXISTE PDF PDE...", validacion=None |
| PDE huérfano | carpeta con PDE pero sin FEV | validación post-proceso | alerta_archivos.mensaje = "PDE HUÉRFANO...", validacion=None |
| Duplicado global | misma carpeta aparece en dos ubicaciones | post-proceso detecta | duplicado_global.ubicaciones lista ambas rutas |

### R5: Timeout y logging

El endpoint DEBE respetar un timeout máximo de 60s (configurable vía `app.config`). Cada paso del pipeline DEBE loguearse con `logger.info` o `logger.warning`. Errores inesperados DEBEN loguearse con `logger.exception`.

| Escenario | Given | When | Then |
|-----------|-------|------|------|
| Timeout alcanzado | procesamiento excede 60s | servidor corta la request | status=error con mensaje de timeout |
| Logging completo | carpeta con 10 PDFs | se procesa | al menos 10 entradas de log con resultado de cada PDF |

### R6: Codificación y paths largos

El sistema DEBE manejar caracteres Unicode y espacios en rutas de archivo. Paths de más de 260 caracteres (Windows) DEBEN manejarse sin crash — si el SO los rechaza, se loguea y omite.

| Escenario | Given | When | Then |
|-----------|-------|------|------|
| Caracteres especiales | carpeta con nombre "Paciente Año 2024-ÑOÑO" | walk itera | se procesa sin error de encoding |
| Path muy largo | archivo en subdirectorio con path > 260 chars | walk lo encuentra | en Windows se loguea warning y se omite; en Linux/LongPathsEnabled se procesa normal |

## Criterios de Aceptación

- [ ] `POST /derechos/auditoria/procesar` retorna estructura con FEV, PDE, soportes y validaciones
- [ ] Frontend muestra árbol expandible con resultados por expediente
- [ ] Un PDF fallido no mata el batch — los demás se procesan
- [ ] Carpeta sin PDFs retorna success con estructura vacía, no error
- [ ] Ruta inexistente retorna error 400 con mensaje
- [ ] PDE huérfano y FEV sin PDE tienen alertas diferenciadas
- [ ] Duplicados globales se detectan y reportan
- [ ] Sin `print()` en código nuevo — solo `logging`
- [ ] Resolución de `reglas_soportes.json` vía `__file__` (no CWD)
