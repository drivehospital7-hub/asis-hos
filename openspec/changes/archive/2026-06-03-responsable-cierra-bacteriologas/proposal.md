# Proposal: Responsable Cierra Facturar modifica reglas de bacteriólogas

## Intent

El detector `detect_bacteriologas_cronograma()` actualmente filtra bacteriólogas válidas con el criterio fijo "CE o PYM" en el cronograma. El negocio exige que ese filtro varíe según quién sea el Responsable Cierra Facturar de la factura: algunos responsables solo validan PYM, otros solo CE, y los facturadores de Urgencias no usan cronograma en absoluto.

## Scope

### In Scope

1. Parametrizar `get_turno_del_dia()` con `siglas_filter` para soportar filtros variables
2. Agregar lógica en `detect_bacteriologas_cronograma()` que reciba `responsable_cierra` y mute el filtro según reglas de negocio
3. Proveer constantes para los 3 nuevos nombres (Chapuel, Tapia, Ordoñez) en `constants/intramural.py` o `constants/urgencias.py`
4. Mover `FACTURADORES_URGENCIAS` de `odontologia/detect_por_responsable.py` a un lugar compartido (`constants/urgencias.py`) y actualizar imports
5. Para responsables en FACTURADORES_URGENCIAS: validar bacterióloga contra `PROFESIONALES_URGENCIAS` sin pasar por cronograma
6. Pasar `responsable_cierra` desde `detect_all_problems_intramural()` al detector

### Out of Scope

- Modificar detectores de otras áreas (odontología, urgencias, equipos básicos)
- Cambiar el formato de los errores retornados
- Modificar el cronograma JSON o su estructura

## Capabilities

### New Capabilities

None — extiende `intramural-bacteriologas-cronograma` existente.

### Modified Capabilities

- `intramural-bacteriologas-cronograma`: el filtro de siglas en cronograma pasa de fijo (CE|PYM) a depender del Responsable Cierra Facturar; se agrega bypass de cronograma para facturadores de Urgencias

## Approach

```
Firma actual:   detect_bacteriologas_cronograma(data_sheet, indices)
Nueva firma:    detect_bacteriologas_cronograma(data_sheet, indices, responsable_cierra)

get_turno_del_dia(mes, anio, dia, siglas_filter=None)
  ├── None   → filter: "CE" in sigla or "PYM" in sigla  (default actual)
  ├── set()  → return ALL turnos sin filtrar
  ├── {"PYM"} → solo "PYM" in sigla
  └── {"CE"}  → solo "CE" in sigla

Lógica por factura en detector:
  1. resp = responsable_cierra.get(factura, "").upper().strip()
  2. if resp == "CHAPUEL CASANOVA ANGIE TATIANA":
         siglas_filter = {"PYM"}
     elif resp in FACTURADORES_URGENCIAS_UPPER:
         # bypass cronograma: si profesional está en PROFESIONALES_URGENCIAS
         # con tipo=BACTERIOLOGA → válido sin check de cronograma
         continue  # skip validación cronograma
     elif resp in ("TAPIA PERDOMO ANYI CATALEYA", "ORDOÑEZ MEZA SILVIA ELEY"):
         siglas_filter = {"CE"}
     else:
         siglas_filter = None  # CE|PYM (default actual)
  3. get_turno_del_dia(..., siglas_filter=siglas_filter)
```

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/cronograma_bacteriologas_service.py` | Modified | `get_turno_del_dia()` agrega `siglas_filter` param |
| `app/services/intramural/bacteriologas_cronograma.py` | Modified | Recibe `responsable_cierra`, aplica reglas de negocio |
| `app/services/intramural/detect_all.py` | Modified | Pasa `responsable_cierra` al detector |
| `app/constants/urgencias.py` | Modified | Agrega FACTURADORES_URGENCIAS + RESPONSABLES_SIGLAS_PYM/CE |
| `app/services/odontologia/detect_por_responsable.py` | Modified | Importa FACTURADORES_URGENCIAS desde constants |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| FACTURADORES_URGENCIAS desactualizado vs el de odontología | Low | Mover a constants, unificar origen |
| `responsable_cierra` no disponible (columna ausente) | Low | Fallback a comportamiento default (CE/PYM) |
| Nombres nuevos con tildes o espacios irregulares | Med | Matching case-insensitive con `.upper().strip()` |

## Rollback Plan

Revertir commit. El cambio toca 5 archivos pero ningún contrato externo. Si `get_turno_del_dia()` cambia firma, verificar que no haya otros llamadores.

## Dependencies

- `detect_all_problems_intramural()` ya construye `responsable_cierra` (no hay que agregar nuevo scan)

## Success Criteria

- [ ] Chapuel → solo PYM válidas; error si bacterióloga tiene solo CE en cronograma
- [ ] Facturador Urgencias → bacterióloga válida si está en PROFESIONALES_URGENCIAS, aunque no esté en cronograma
- [ ] Tapia/Ordoñez → solo CE válidas; error si tiene solo PYM
- [ ] Otros responsables → mismo comportamiento actual (CE o PYM)
- [ ] `FACTURADORES_URGENCIAS` vive en `constants/urgencias.py` y odontología lo importa de ahí
