# Proposal: Mejora de rendimiento de procesamiento de Excel y control de carga

## Intent

Múltiples usuarios procesan facturas simultáneamente. Sin límite de tamaño (prod), rate limit ni control de concurrencia. Un archivo gigante o requests concurrentes pueden saturar CPU/memoria.

## Scope

### In Scope
- Límite de tamaño de archivo Excel en `save_temp_excel()` con constante centralizada
- Rate limiting por sesión (N requests/minuto a endpoints POST de procesamiento)
- Semáforo de concurrencia global (máx. N procesamientos simultáneos)
- Feedback al usuario: mensajes claros en 429, 503, y tamaño excedido

### Out of Scope
- Cola asíncrona (Celery/Redis), caché de resultados, workers dedicados, compresión

## Capabilities

### New Capabilities
- `upload-rate-limiting`: Control de tasa de solicitudes de procesamiento por sesión

### Modified Capabilities
- None — capa de infraestructura, no cambia comportamiento funcional

## Approach

Tres capas independientes y acumulativas, cada una con su propio commit:

1. **File size**: Activar validación comentada en `save_temp_excel()` usando `MAX_EXCEL_UPLOAD_SIZE_MB` en `base.py`. Setear `MAX_CONTENT_LENGTH` en prod a 100MB.

2. **Rate limiter**: Decorador `@rate_limit(limit, window)` que cuenta timestamps de requests POST en `session["_rate_limiter"]`. Excede → 429.

3. **Concurrency**: `threading.Semaphore(N)` global en `app/services/processor_gate.py`. `detect_problems_only()` acquire con timeout → 503 si agota.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/constants/base.py` | Modified | Nueva `MAX_EXCEL_UPLOAD_SIZE_MB` |
| `config/prod.py` | Modified | `MAX_CONTENT_LENGTH = 100 * 1024 * 1024` |
| `app/utils/input_data.py` | Modified | Activar validación de tamaño |
| `app/services/processor_gate.py` | New | Semáforo + rate limiter |
| `app/services/exporter.py` | Modified | Wrapper con acquire/release |
| `app/routes/excel_headers.py` | Modified | Decorador rate limit |
| `app/routes/urgencias.py` | Modified | Decorador rate limit |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Rate limiter en session es volátil | Medium | Aceptable 1ra iteración; migrar a Redis después |
| Semáforo bloquea con timeout bajo | Low | N=3, timeout=30s — valores generosos |
| MAX_CONTENT_LENGTH rechaza legítimos | Low | 100MB — facturas rara vez >20MB |

## Rollback Plan

1. Revertir `config/prod.py` → `MAX_CONTENT_LENGTH = None`
2. Eliminar decorador `@rate_limit` en routes
3. Eliminar `processor_gate.py` (módulo nuevo)
4. Revertir `save_temp_excel()` a estado anterior
5. Cada capa en commit separado → rollback granular

## Dependencies

- Ninguna externa. Solo stdlib: `threading`, `time`, `dataclasses`

## Success Criteria

- [ ] Archivo > 100MB rechazado con mensaje claro
- [ ] > N requests/min desde misma sesión → 429
- [ ] > 3 procesamientos simultáneos → 503
- [ ] Tests unitarios para cada capa
- [ ] Logging [BACK] en cada límite alcanzado
