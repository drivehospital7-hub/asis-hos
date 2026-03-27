---
applyTo: '**'
---
# ARCHITECTURE RULES

## Scope
Aplica a TODO el proyecto sin excepción.

## Estructura del proyecto

El sistema sigue arquitectura modular:

- routes/ → endpoints
- services/ → lógica de negocio
- utils/ → helpers
- data/ → archivos
- templates/ ->html

## Reglas obligatorias

- PROHIBIDO lógica en routes
- Los routes solo llaman servicios
- Cada servicio = una responsabilidad
- No duplicar lógica
- Separar lectura de archivos y lógica

## Diseño de módulos

- Inputs y outputs claros
- Funciones reutilizables
- No dependencias innecesarias

## Escalabilidad

- Permitir agregar nuevas reglas sin romper código existente
- Diseñar para extensión, no modificación

## Scope
Aplica a cualquier archivo de código.

## Estilo

- Funciones < 50 líneas
- Nombres descriptivos
- Evitar abreviaciones

## Legibilidad

- Código simple > complejo
- Evitar anidación profunda
- Usar variables intermedias

## Reutilización

- No duplicar código
- Extraer helpers a utils/

## Comentarios

- Explicar lógica no obvia
- No comentar lo evidente

## Librerías

- Priorizar estándar de Python
- No agregar dependencias sin justificación