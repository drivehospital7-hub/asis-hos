# Procedimientos Unificados — Specification

## Purpose

Unificar la lectura de procedimientos/tarifas hacia la cadena SQLAlchemy (`eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`) y eliminar la tabla PostgreSQL `procedimientos` (psycopg2) como fuente redundante.

## Requirements

### Requirement: Vista SQL v_procedimientos

La vista SQL `v_procedimientos` DEBE presentar la cadena de 5 tablas como estructura plana con columnas `id`, `eps`, `codigo_cups`, `descripcion`, `tarifa`. DEBE usar `DISTINCT ON (eps, codigo_cups)` para eliminar duplicados cuando un mismo CUPS aparezca en múltiples `notas_tecnicas`.

| Columna | Origen | Tipo |
|---------|--------|------|
| `id` | `ROW_NUMBER()` | INTEGER |
| `eps` | `eps_contratado.eps` | TEXT |
| `codigo_cups` | `procedimiento.cups` | TEXT |
| `descripcion` | `procedimiento.procedimiento` | TEXT |
| `tarifa` | `notas_tecnicas.tariff` | NUMERIC(12,2) |

#### Scenario: Lectura plana de la cadena

- **GIVEN** existen `eps_contratado` "EMSSANAR", `procedimiento` cups "890201", y `notas_tecnicas` tariff 45000 vinculados por la cadena
- **WHEN** se consulta `SELECT * FROM v_procedimientos WHERE eps = 'EMSSANAR' AND codigo_cups = '890201'`
- **THEN** retorna una fila con `eps='EMSSANAR'`, `codigo_cups='890201'`, `tarifa=45000`

#### Scenario: Deduplicación de CUPS repetido

- **GIVEN** el mismo `procedimiento` cups "890201" está vinculado a 2 `nota_hoja` distintas (con tarifas 45000 y 46000) para la misma EPS "EMSSANAR"
- **WHEN** se consulta la vista para `eps='EMSSANAR'` y `codigo_cups='890201'`
- **THEN** retorna 1 sola fila (no 2)

#### Scenario: EPS sin procedimientos vinculados

- **GIVEN** `eps_contratado` "MALLAMAS" existe pero no tiene `eps_nota` ni `notas_tecnicas`
- **WHEN** se consulta `SELECT * FROM v_procedimientos WHERE eps = 'MALLAMAS'`
- **THEN** retorna 0 filas

---

### Requirement: Read API mantiene contrato

El módulo `procedimientos_db.py` DEBE mantener idéntica interfaz pública — `get_procedimiento()`, `get_all_by_codigo()`, `get_all_by_eps()`, `get_eps_disponibles()`, `verificar_codigo()`, `verificar_tarifa()` — pero las consultas DEBEN leer de `v_procedimientos`. Los tipos de retorno (`Procedimiento`, `tuple[bool, str]`, `List[str]`) NO DEBEN cambiar.

#### Scenario: get_procedimiento encuentra resultado

- **GIVEN** la vista tiene un registro para `eps='EMSSANAR'` y `codigo_cups='890201'`
- **WHEN** se llama `get_procedimiento("EMSSANAR", "890201")`
- **THEN** retorna `Procedimiento(eps="EMSSANAR", codigo_cups="890201", ...)`

#### Scenario: get_procedimiento no encuentra

- **GIVEN** la vista no tiene registros para `eps='EMSSANAR'` y `codigo_cups='999999'`
- **WHEN** se llama `get_procedimiento("EMSSANAR", "999999")`
- **THEN** retorna `None`

#### Scenario: verificar_tarifa dentro de tolerancia

- **GIVEN** la vista tiene `tarifa=45000.00` para `eps='EMSSANAR'`, `codigo_cups='890201'`
- **WHEN** se llama `verificar_tarifa("EMSSANAR", "890201", 45000.50, tolerancia=0.01)`
- **THEN** retorna `(True, ...)` porque `|45000.50 - 45000.00| ≤ 0.01`

#### Scenario: verificar_tarifa fuera de tolerancia

- **GIVEN** misma tarifa en vista = 45000
- **WHEN** `verificar_tarifa("EMSSANAR", "890201", 50000)`
- **THEN** retorna `(False, ...)` porque diff = 5000 > 0.01

#### Scenario: get_eps_disponibles

- **GIVEN** la vista tiene registros para "EMSSANAR", "MALLAMAS", "ASMET_SALUD"
- **WHEN** se llama `get_eps_disponibles()`
- **THEN** retorna `["ASMET_SALUD", "EMSSANAR", "MALLAMAS"]` ordenado alfabéticamente

---

### Requirement: Eliminación de endpoints de escritura

Los endpoints `POST`, `PUT`, `DELETE` en `/procedimientos` DEBEN ser removidos y DEBEN retornar `410 Gone`. El archivo `procedimientos_crud.py` DEBE ser eliminado. Los endpoints `GET` existentes DEBEN seguir funcionando sin cambios.

#### Scenario: POST retorna 410 Gone

- **GIVEN** el blueprint de procedimientos está registrado
- **WHEN** se hace `POST /procedimientos` con body JSON válido
- **THEN** retorna `{"status": "error", "data": {}, "errors": ["Este endpoint ya no está disponible"]}` con status 410

#### Scenario: PUT retorna 410 Gone

- **WHEN** se hace `PUT /procedimientos/123`
- **THEN** retorna 410 Gone

#### Scenario: DELETE retorna 410 Gone

- **WHEN** se hace `DELETE /procedimientos/123`
- **THEN** retorna 410 Gone

#### Scenario: GET endpoints sin cambios

- **GIVEN** la vista `v_procedimientos` está creada
- **WHEN** se hace `GET /procedimientos?eps=EMSSANAR&all=true`
- **THEN** retorna misma estructura JSON que antes (array de objetos con id, eps, codigo_cups, descripcion, tarifa)

---

### Requirement: Migración del script verificar_codigos_urgencias

El script `verificar_codigos_urgencias.py` DEBE reemplazar `get_procedimiento()` (psycopg2) por una query SQLAlchemy directa sobre los modelos `EpsContratado`, `Procedimiento`, `NotasTecnicas` y las tablas de join. DEBE mapear `"EMSSANAR_CAPITA"` al `cod_contrato` correspondiente. El comportamiento exterior DEBE ser idéntico.

#### Scenario: Código encontrado en la cadena

- **GIVEN** la cadena SQLAlchemy tiene `eps_contratado.cod_contrato` mapeado a `"EMSSANAR_CAPITA"` y `procedimiento.cups = "890201"` con `tariff = 45000`
- **WHEN** el script verifica el código "890201" para ESS118
- **THEN** lo reporta como "encontrado"

#### Scenario: Código no encontrado

- **GIVEN** la cadena no contiene `procedimiento.cups = "999999"`
- **WHEN** el script verifica "999999"
- **THEN** lo reporta como "NO encontrado"

#### Scenario: Mismo resultado que antes

- **GIVEN** un Excel de prueba con 10 códigos ESS118
- **WHEN** se ejecuta el script migrado
- **THEN** produce el mismo conjunto de `codigos_no_encontrados` y `codigos_encontrados` que la versión anterior

---

### Requirement: Limpieza de funciones muertas en frontend

Las funciones `fetchProcPg`, `fetchEpsDisponibles`, `createProcPg`, `updateProcPg`, `deleteProcPg` DEBEN ser eliminadas de `api-catalogo.ts` y sus tests correspondientes DEBEN ser removidos de `api-catalogo.test.ts`. Las funciones restantes NO DEBEN verse afectadas.

#### Scenario: Funciones eliminadas del módulo

- **GIVEN** `api-catalogo.ts` contiene las 5 funciones
- **WHEN** se eliminan
- **THEN** `api-catalogo.ts` compila sin errores de TypeScript

#### Scenario: Tests eliminados

- **GIVEN** `api-catalogo.test.ts` contiene `describe("fetchProcPg", ...)` y los otros 4 bloques
- **WHEN** se eliminan esos 5 bloques `describe`
- **THEN** los tests restantes (fetchEps, createEps, etc.) pasan sin cambios

#### Scenario: Funciones no referenciadas en UI

- **GIVEN** las funciones eliminadas son solo usadas por el test file
- **WHEN** se busca su uso en `frontend/src/`
- **THEN** no se encuentra ningún otro import (solo `api-catalogo.test.ts`)

---

### Requirement: Script de migración para la vista

DEBE existir un script SQL en `migrations/` que cree `v_procedimientos`. DEBE aplicar el JOIN de las 5 tablas con `DISTINCT ON (eps, codigo_cups)`. DEBE ser reversible con `DROP VIEW IF EXISTS v_procedimientos`.

#### Scenario: Creación exitosa de la vista

- **GIVEN** las 5 tablas existen en la base de datos
- **WHEN** se ejecuta el script de migración
- **THEN** `v_procedimientos` existe y es consultable

#### Scenario: Rollback de la vista

- **GIVEN** la vista fue creada
- **WHEN** se ejecuta `DROP VIEW IF EXISTS v_procedimientos`
- **THEN** la vista deja de existir sin afectar las tablas subyacentes

#### Scenario: Vista re-ejecutable sin errores

- **GIVEN** la vista ya existe
- **WHEN** se ejecuta `CREATE OR REPLACE VIEW v_procedimientos AS ...`
- **THEN** la vista se recrea sin errores y mantiene los mismos resultados
