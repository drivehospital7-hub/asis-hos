# Proposal: CAP exception — ESS118 / EPSS41 in CUPS sin contrato

## Intent

`detect_cups_sin_contrato()` valida cada fila contra la cadena contractual de la entidad (`eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`). Pero facturas CAP ("CAP-...") de EMSSANAR (ESS118) y NUEVA EPS (EPSS41) se rigen por un convenio capitado especial, no por el contrato estándar. Sin excepción, generan falsos positivos.

## Scope

### In Scope
- Pre-load adicional: procedimientos vinculados a `nota_hoja id=2` ("NUEVA EPS CAPITA") y `nota_hoja id=3` ("EMSSANAR CAPITA")
- En el loop: si factura empieza con "CAP" + `cod_entidad = ESS118` → validar contra nota_hoja id=3
- En el loop: si factura empieza con "CAP" + `cod_entidad = EPSS41` → validar contra nota_hoja id=2
- 6 nuevos tests

### Out of Scope
- Cambios a detect_all.py de cualquier área (0 archivos)
- Nuevos detectores o archivos
- Cambios de signature o interfaz

## Capabilities

### New Capabilities
None

### Modified Capabilities
- **`procedimientos-contratados`**: Se agregan dos excepciones — cuando `Número Factura` empieza con "CAP" y `cod_entidad` es ESS118 o EPSS41, la validación usa procedimientos de su nota_hoja capitada específica en vez de la cadena contractual de la entidad. No cambia el output format ni el contrato del detector.

## Approach

Tres cambios dentro de `detect_cups_sin_contrato()`:

1. **Dos pre-loads adicionales** (junto al existente de nota_hoja id=1): queries `notas_tecnicas → procedimiento` filtrados por `id_nota_hoja = 2` y `id_nota_hoja = 3`, guardados como `nota2_cups` y `nota3_cups`.
2. **Branch CAP+ESS118**: si `factura.startswith("CAP")` y `cod_entidad == "ESS118"` → validar contra `nota3_cups`.
3. **Branch CAP+EPSS41**: si `factura.startswith("CAP")` y `cod_entidad == "EPSS41"` → validar contra `nota2_cups`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/transversales/procedimiento_contratado.py` | Modified | 2 pre-loads + 2 branches. ~20-25 líneas nuevas |
| `tests/services/test_detect_cups_sin_contrato.py` | Modified | 6 nuevos tests (~70 líneas) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Factura no tiene columna `numero_factura` | Muy baja | Falla temprano (misma validación existente) |
| nota_hoja id=2 / id=3 sin procedimientos | Baja | Set vacío → CAP se valida contra nada → error (fails closed) |
| Nueva entidad CAP en futuro | Baja | Este cambio es específico; futuras entidades requerirían otro branch |

## Rollback Plan

Revertir líneas agregadas en `procedimiento_contratado.py`. Sin migración, sin impacto en DB.

## Dependencies

Ninguna. `numero_factura` ya tiene índice en todos los callers.

## Success Criteria

- [ ] Factura CAP + ESS118 + CUPS en nota_hoja id=3 → sin error
- [ ] Factura CAP + EPSS41 + CUPS en nota_hoja id=2 → sin error
- [ ] Factura CAP + ESS118 + CUPS NO en nota_hoja id=3 → error
- [ ] Factura NO-CAP + ESS118 → validación normal (sin excepción)
- [ ] Tests existentes (28) siguen pasando
- [ ] Sin cambios de signature ni archivos nuevos
