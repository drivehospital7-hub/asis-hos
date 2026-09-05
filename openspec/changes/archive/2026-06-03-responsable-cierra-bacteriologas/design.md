# Design: Responsable Cierra modifica reglas de bacteriólogas

## Arquitectura

El responsable fluye desde el orquestador hasta el filtro de siglas en el cronograma:

```
detect_all_problems_intramural()
  │
  ├── 1. Build responsable_cierra: dict[factura → nombre]
  │      (ya existe en detect_all.py, líneas 72-85)
  │
  └── 2. detect_bacteriologas_cronograma(data_sheet, indices, responsable_cierra)
         │
         ├── Por cada factura válida (Intramural + Lab=Si + Tipo 02/05):
         │     │
         │     ├── resp = responsable_cierra.get(factura, "")
         │     │
         │     ├── ¿resp in FACTURADORES_URGENCIAS?
         │     │   └── Sí → validar contra PROFESIONALES_URGENCIAS solamente
         │     │         (sin llamado a get_turno_del_dia)
         │     │
         │     ├── ¿resp == CHAPUEL?
         │     │   └── Sí → siglas_filter = {"PYM"}
         │     │
         │     ├── ¿resp in (TAPIA, ORDOÑEZ)?
         │     │   └── Sí → siglas_filter = {"CE"}
         │     │
         │     └── else → siglas_filter = None  (default CE|PYM)
         │
         └── 3. get_turno_del_dia(mes, anio, dia, siglas_filter=siglas_filter)
                │
                └── Filtra turnos del cronograma según siglas_filter
```

### Bypass de cronograma para Urgencias

Cuando el responsable es un `FACTURADORES_URGENCIAS`, la validación de bacterióloga NO pasa por cronograma. Solo se verifica que el código profesional exista en `PROFESIONALES_URGENCIAS` con `tipo=BACTERIOLOGA`. Eso ya ocurre en las líneas 254-292 del detector actual — simplemente se salta la llamada a `get_turno_del_dia` (línea 304).

## Interfaces / Contratos

### `get_turno_del_dia` (modificada)

```python
def get_turno_del_dia(
    mes: int | None = None,
    anio: int | None = None,
    dia: int | None = None,
    siglas_filter: set[str] | None = None,
) -> list[dict]:
```

| `siglas_filter` | Comportamiento |
|---|---|
| `None` | Default actual: `"CE" in codigo or "PYM" in codigo` |
| `set()` (vacío) | Retorna todos los turnos sin filtrar |
| `{"PYM"}` | Solo `"PYM" in codigo` |
| `{"CE"}` | Solo `"CE" in codigo` |

### `detect_bacteriologas_cronograma` (modificada)

```python
def detect_bacteriologas_cronograma(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    responsable_cierra: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
```

El parámetro `responsable_cierra` es opcional. Si es `None` o está vacío, comportamiento default (CE|PYM).

## Decisiones de arquitectura

### Decisión: Dónde alojar las constantes

| Constante | Ubicación | Rationale |
|---|---|---|
| `FACTURADORES_URGENCIAS` | `app/constants/urgencias.py` | Es dominio Urgencias; ya re-exportado via `__init__.py`; odontología lo importará de ahí |
| `RESPONSABLE_CHAPUEL` | `app/constants/intramural.py` | Solo aplica en Intramural; no necesita re-export |
| `RESPONSABLE_TAPIA` | `app/constants/intramural.py` | Idem |
| `RESPONSABLE_ORDONEZ` | `app/constants/intramural.py` | Idem |

### Decisión: Import compartido de FACTURADORES_URGENCIAS

Se mueve el `set` actual de `odontologia/detect_por_responsable.py` a `constants/urgencias.py` como `FACTURADORES_URGENCIAS: set[str]`. Odontología cambia su import de definición local a `from app.constants.urgencias import FACTURADORES_URGENCIAS`.

## Módulo de constantes

En `app/constants/intramural.py` se agrega:

```python
# Responsables que restringen siglas válidas en cronograma bacteriólogas
RESPONSABLE_CHAPUEL = "CHAPUEL CASANOVA ANGIE TATIANA"
RESPONSABLE_TAPIA = "TAPIA PERDOMO ANYI CATALEYA"
RESPONSABLE_ORDONEZ = "ORDOÑEZ MEZA SILVIA ELEY"
```

En `app/constants/urgencias.py` se agrega:

```python
# Facturadores de urgencias que NO usan cronograma para bacteriólogas
FACTURADORES_URGENCIAS: set[str] = {
    "ARIAS CULCHA ANGIE CAROLINA",
    "ESPAÑA DIAZ LORENY ALEJANDRA",
    "MEZA FERNANDEZ CARLOS OMAR",
    "PAEZ YULIETH DANIELA",
}
```

## Lógica de decisión

Pseudocódigo dentro del loop de filas en `detect_bacteriologas_cronograma()`:

```python
# 1. Validación vs PROFESIONALES_URGENCIAS (actual, líneas 254-292)
#    Se mantiene igual: verifica código existe y tipo=BACTERIOLOGA

# 2. Determinar si bypass o siglas_filter
resp = (responsable_cierra or {}).get(factura, "").upper().strip()

if resp in FACTURADORES_URGENCIAS:
    # Bypass total de cronograma — no llamar get_turno_del_dia
    continue  # bacterióloga válida si pasó paso 1

if resp == RESPONSABLE_CHAPUEL:
    siglas_filter = {"PYM"}
elif resp in {RESPONSABLE_TAPIA, RESPONSABLE_ORDONEZ}:
    siglas_filter = {"CE"}
else:
    siglas_filter = None  # CE|PYM (comportamiento actual)

# 3. Llamada a cronograma
turnos = get_turno_del_dia(mes, anio, dia, siglas_filter=siglas_filter)
```

Arbol de decisión:
```
¿Código en PROFESIONALES_URGENCIAS?
├── No → ERROR (profesional no listado)
└── Sí → ¿Tipo == BACTERIOLOGA?
    ├── No → ERROR (no es bacterióloga)
    └── Sí → ¿Responsable en FACTURADORES_URGENCIAS?
        ├── Sí → VÁLIDO (sin cronograma)
        └── No → ¿Responsable == CHAPUEL?
            ├── Sí → Filtrar cronograma solo PYM
            ├── No → ¿Responsable in (TAPIA, ORDOÑEZ)?
            │   ├── Sí → Filtrar cronograma solo CE
            │   └── No → Filtrar cronograma CE|PYM (default)
            └── Validar vs turnos filtrados del cronograma
```

## Archivos modificados

| Archivo | Acción | Descripción |
|---|---|---|
| `app/constants/urgencias.py` | Modificar | Agregar `FACTURADORES_URGENCIAS`, eliminar definición duplicada futura |
| `app/constants/intramural.py` | Modificar | Agregar `RESPONSABLE_CHAPUEL`, `RESPONSABLE_TAPIA`, `RESPONSABLE_ORDONEZ` |
| `app/services/cronograma_bacteriologas_service.py` | Modificar | Agregar `siglas_filter` a `get_turno_del_dia()` |
| `app/services/intramural/bacteriologas_cronograma.py` | Modificar | Recibir `responsable_cierra`, aplicar lógica de decisión |
| `app/services/intramural/detect_all.py` | Modificar | Pasar `responsable_cierra` al detector |
| `app/services/odontologia/detect_por_responsable.py` | Modificar | Importar `FACTURADORES_URGENCIAS` desde constants, eliminar definición local |

## Estrategia de pruebas

| Capa | Qué probar | Cómo |
|---|---|---|
| Unit - `get_turno_del_dia` | Filtro con `siglas_filter=None`, `{"PYM"}`, `{"CE"}`, `set()` | Mock cronograma JSON con turnos mixtos CE/PYM |
| Unit - `detect_bacteriologas_cronograma` | Cada rama del árbol de decisión (Chapuel, Tapia, Ordoñez, Urgencias, default) | Mock de `get_turno_del_dia` y `Worksheet` |
| Integration | Flujo completo desde `detect_all` hasta errores | Usar fixture de Excel con datos realistas |
| Regression | Odontología: `FACTURADORES_URGENCIAS` import sigue funcionando | Test existente de `_partition_rows` |

### Casos de prueba

1. Chapuel + bacterióloga solo PYM → sin error
2. Chapuel + bacterióloga solo CE → error
3. Tapia + bacterióloga solo CE → sin error
4. Tapia + bacterióloga solo PYM → error
5. Ordoñez + bacterióloga solo CE → sin error
6. Facturador Urgencias + bacterióloga válida en PROFESIONALES → sin error (aunque no esté en cronograma)
7. Facturador Urgencias + bacterióloga NO en PROFESIONALES → error
8. Otro responsable + bacterióloga CE/PYM → mismo comportamiento actual
9. `responsable_cierra=None` → fallback a default (CE|PYM)
10. Responsable con tildes/espacios irregulares → case-insensitive match

## Riesgos y mitigaciones

| Riesgo | Prob | Mitigación |
|---|---|---|
| `FACTURADORES_URGENCIAS` duplicado durante migración | Baja | Migrar en un solo commit: mover a constants, actualizar imports, eliminar definición local |
| `responsable_cierra` ausente en Excel | Baja | Parámetro opcional `None` → default CE/PYM |
| Nombres con tildes, espacios, mayúsculas irregulares | Media | `.upper().strip()` antes de comparar constantes (que están en UPPER) |
| `get_turno_del_dia` tiene otros llamadores que se rompan | Baja | `siglas_filter=None` es default → 100% compatible hacia atrás |
