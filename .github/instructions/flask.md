---
description: Aplica SOLO cuando:  - Se trabaja en routes/ - Se crean endpoints Flask - Se manejan requests/responses HTTP
applyTo: "services/**, routes/**, data/**"
---
# FLASK RULES

## Scope


## Uso de routes

Las rutas deben:

- Recibir request
- Validar inputs básicos
- Llamar servicios
- Retornar respuesta

## Prohibiciones

- NO lógica de negocio en routes
- NO procesamiento de archivos
- NO validaciones complejas

## Respuestas

Formato obligatorio:

{
  "status": "success | error",
  "data": {},
  "message": ""
}

## Manejo de errores

- No lanzar errores sin control
- Retornar errores estructurados