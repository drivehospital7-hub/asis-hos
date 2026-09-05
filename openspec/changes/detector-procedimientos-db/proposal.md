# Proposal: Detector transversal de procedimientos vs DB

## Intent

Validar que cada par (Cód Entidad Cobrar, Código CUPS) en el Excel de facturas exista como una relación contratada en la DB PostgreSQL. Esto evita glosas por cobro improcedente — si una EPS no tiene contratado un procedimiento, la factura debe marcarse como error antes de enviarse.

## Scope

### In Scope
- Detector en `app/services/transversales/` con pre-load de pares válidos desde DB
- Integración en `detect_all.py` de cada área (odontología, urgencias, equipos_básicos, etc.)
- Manejo de DB no disponible (fallback silencioso)
- Tests unitarios e integración

### Out of Scope
- Modificar estructura de DB o crear tablas nuevas
- UI específica para este detector
- Validación de tarifas (solo existencia de relación EPS-procedimiento)

### Capabilities
- **New** `procedimientos-contratados`: valida que un par (cod_contrato, cups) exista en la cadena `eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`

## Approach

### Pre-load (una sola consulta al iniciar el detector)

```python
valid_pairs = set(
    (row.cod_contrato, row.cups)
    for row in db.query(EpsContratado.cod_contrato, Procedimiento.cups)
    .join(EpsNota, EpsNota.id_eps_contratado == EpsContratado.id)
    .join(NotaHoja, NotaHoja.id == EpsNota.id_nota_hoja)
    .join(NotasTecnicas, NotasTecnicas.id_nota_hoja == NotaHoja.id)
    .join(Procedimiento, Procedimiento.id == NotasTecnicas.id_procedimiento)
    .distinct()
    .all()
)
```

Mismo patrón que `app/services/urgencias/codigos_sin_db.py`.

### Por cada fila del Excel
1. Leer `codigo_entidad_cobrar` (columna "Cód Entidad Cobrar") y `codigo` (columna "Código")
2. Normalizar ambos a string, trim
3. Si `(cod_entidad_cobrar, codigo)` NO está en `valid_pairs` → agregar error

### Output del detector
```python
{
    "factura": str,
    "codigo_entidad_cobrar": str,
    "codigo": str,
    "procedimiento": str,
    "problema": "Procedimiento {codigo} no está contratado para EPS {cod_entidad_cobrar}",
}
```

## Architecture

### Crear
- `app/services/transversales/procedimiento_contratado.py` — detector `detect_procedimiento_no_contratado(data_sheet, indices) -> list[dict]`
- `tests/services/test_transversales_procedimiento_contratado.py`

### Modificar
- `app/services/odontologia/detect_all.py` — agregar llamado
- `app/services/urgencias/detect_all.py` — agregar llamado
- `app/services/equipos_basicos/detect_all.py` — agregar llamado
- (y demás áreas según decisión)

### Columnas requeridas
| Excel | Índice key | Tabla DB |
|---|---|---|
| Cód Entidad Cobrar | `codigo_entidad_cobrar` | `eps_contratado.cod_contrato` |
| Código | `codigo` | `procedimiento.cups` |

## Decisions Needed

1. **Nombre del detector** — `detect_procedimiento_no_contratado`? `detect_cups_sin_contrato`? ¿Otro?
2. **¿Aplica a TODAS las áreas o solo algunas?** — El par (Cód Entidad Cobrar, Código) existe en todos los Excels, pero la decisión es si activarlo en odontología, urgencias, equipos básicos, hospitalización, intramural, ambulatoria, etc.
3. **¿Incluir nombre de EPS en el error?** — Podemos hacer JOIN con `EpsContratado.eps` para mostrar nombre legible, pero agrega complejidad al pre-load.

## Effort Estimate

**Bajo.** Patrón existente probado en `codigos_sin_db.py` (~120 líneas). Los cambios son:
- 1 archivo nuevo de detector (~50-70 líneas)
- 1 archivo de tests (~80-100 líneas)
- N modificaciones triviales en `detect_all.py` (1 línea cada una)

## Rollback Plan

- Por detector: borrar el archivo y revertir las líneas agregadas en `detect_all.py`
- Sin impacto en DB ni datos existentes

## Risks

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| DB no disponible al cargar el detector | Baja | Try/except -> retornar `[]` silenciosamente (como `codigos_sin_db.py`) |
| Set de pares demasiado grande en memoria | Baja | Son pocos miles; usar `set` de tuplas `(str, str)` |
| Falsos positivos si el Excel usa formato distinto al de DB | Media | Normalizar con `.strip().upper()` en ambos lados |

## Success Criteria

- [ ] Detector creado con pre-load de DB y verificación por fila
- [ ] Integrado en `detect_all.py` del área correspondiente
- [ ] Tests pasan (unit + integración con DB de prueba)
- [ ] Output sigue el formato `list[dict]` del contrato de detectores
