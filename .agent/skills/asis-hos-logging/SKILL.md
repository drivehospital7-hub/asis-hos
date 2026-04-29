---
name: asis-hos-logging
description: >
  Sistema de logging estandarizado para asis-hos. Limpiar bruit, establecer convenciones [BACK]/[FRONT]/[ERROR].
  Trigger: Cuando se escribe o limpia código que tiene print(), console.log(), o cuando se implementan nuevos flujos de logging.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## 🎯 Objetivo

Establecer logging claro y consistente que permita:
- Identificar la capa (frontend/backend)
- Sigue el flujo de ejecución
- Diferencia errores reales de debugging

---

## When to Use

- **Escribir nuevo código** → usar convenciones de esta skill
- **Limpiar código existente** → eliminar print() y genéricos
- **Debug en desarrollo** → usar [DEBUG] con temporal flags
- **Monitoreo en producción** → solo ERROR y flujo clave

---

## Convenciones (OBLIGATORIAS)

### [BACK] Backend (Flask / Python)

```python
import logging
logger = logging.getLogger(__name__)

# Flujo normal (producción OK)
logger.info("[BACK] Request recibido en /facturas/upload")
logger.info("[BACK] Archivo validado: %s", filename)

# Advertencias (produccion OK - pero revisar)
logger.warning("[BACK] Archivo sin formato esperado: %s", filename)
logger.warning("[BACK] Campo faltante '%s', usando default", field)

# Errores críticos (produccion OK - REQUIEREN accion)
logger.error("[BACK][ERROR] Fallo al procesar PDF: %s", e)
logger.error("[BACK][ERROR] Conexión DB perdida")
```

### [FRONT] Frontend (JavaScript)

```javascript
// Flujo normal
console.log("[FRONT] Usuario hace click en subir archivo")
console.log("[FRONT] Enviando request al backend")

// Advertencias
console.warn("[FRONT] Datos incompletos en formulario")

// Errores
console.error("[FRONT][ERROR] Fallo en petición fetch:", error)
```

### [DEBUG] Desarrollo temporal

```python
# SOLO para desarrollo - remover antes de merge
logger.debug("[DEBUG] Fila %d - tipo_factura=%s", row, tipo)
```

---

## Anti-Patrones (NO HACER)

### ❌ NO usar print()

```python
# MALO - no incluye contexto de capa
print("llegó")
print("procesando archivo")

# BUENO - incluye [BACK]
logger.info("[BACK] Procesando archivo: %s", filename)
```

### ❌ NO usar console.log() genéricos

```javascript
// MALO
console.log("aqui")
console.log("hola")

# BUENO
console.log("[FRONT] Acción: click botón guardar")
```

### ❌ NO logs sin contexto

```python
# MALO
logger.info("ok")
logger.warning("error")
logger.error("fallo")

# BUENO
logger.info("[BACK] Request procesado exitosamente")
logger.warning("[BACK] Archivo sin formato esperado: %s", ext)
logger.error("[BACK][ERROR] Fallo al conectar DB: %s", e)
```

---

## Reglas de Limpieza (OBLIGATORIA)

### ✅ Antes de completar funcionalidad

Eliminar:
- `print()` 
- `console.log()` innecesarios
- `logger.debug()` temporal
- Logs duplicados
- Logs sin acción posible

Mantener:
- Flujo clave del sistema
- Errores que requieren intervención
- Puntos de decisión importantes

### ✅ Antes de nueva funcionalidad

1. Revisar logs existentes
2. Eliminar ruido previo
3. Agregar logs con convenciones correctas

---

## Estructura de Archivos

### handlers/ (logging/handlers/)

```python
# logging/handlers/__init__.py
from .filters import LevelFilter
from .formatters import DetailedFormatter

__all__ = ["LevelFilter", "DetailedFormatter"]
```

### filters.py

```python
class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno == self.level
```

### formatters.py

```python
from logging import Formatter

class DetailedFormatter(Formatter):
    def format(self, record):
        return f"{record.asctime} - {record.name} - {record.levelname} - {record.message}"
```

---

## Configuración (ya existe)

La configuración base está en **run_dev.py** (líneas 12-56):

- `logs/debug.log` → DEBUG
- `logs/info.log` → INFO  
- `logs/warning.log` → WARNING
- `logs/error.log` → ERROR

Consola muestra solo WARNING+ (en producción).

---

## Checklist de Limpieza

- [ ] Eliminar TODOS los print() del código funcional
- [ ] Verificar que cada logger.info/warning/error tiene [BACK] o [FRONT]
- [ ] Revisar que mensajes explican QUÉ está pasando
- [ ] Eliminar logger.debug() temporales
- [ ] Probar que logs aparecen correctamente

---

## Commands

```bash
# Ver todos los print() en el proyecto
grep -rn "print(" app/ --include="*.py" | grep -v "Blueprint"

# Ver todos los console.log() en frontend
grep -rn "console.log(" app/ --include="*.js"

# Ver logs de desarrollo
tail -f logs/debug.log

# Ver solo errores
tail -f logs/error.log
```

---

## Recursos

- **Configuración**: `run_dev.py` - LevelFilter, handlers
- **Constantes**: `app/constants.py` - valores del sistema
- **Limpieza**: Ver grep commands arriba

---

## Regla Mental

> "Si no puedo entender el flujo leyendo los logs, el sistema está mal loggeado"

Si un log NO responde:
- ¿Qué está pasando?
- ¿Dónde?
- ¿Por qué es importante?

→ DEBE ELIMINARSE