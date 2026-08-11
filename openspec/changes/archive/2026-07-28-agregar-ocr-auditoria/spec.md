# Auditoría — Extractor de PDF con Fallback OCR

## Purpose

Extracción de texto de PDFs de auditoría (PDE y soportes). Fast path con `fitz.get_text()` para PDFs digitales; fallback OCR por página con `pytesseract` cuando el texto extraído es insuficiente (PDF escaneado) y el binario de Tesseract está disponible en disco.

> **Nota de dominio**: no existía spec previo para `auditoria-extractor` — este es un spec NUEVO (full, no delta). El proposal declara "Modified Capabilities: None" porque la operación observable (extraer texto) es la misma; lo que cambia es la tasa de éxito en escaneados.
>
> **Aclaración**: el brief mencionaba "límite de 2 páginas PDE". El comportamiento real (código + design.md) es **corte temprano al detectar datos PDE completos**, sin límite numérico fijo. El spec refleja el comportamiento real.

## Requirements

### R1: Fallback OCR por página en extraer_texto_pdf

La función MUST intentar primero `page.get_text()` por página (fast path). Si el texto de una página es ≤ 50 caracteres y el binario de Tesseract existe en disco, MUST intentar OCR sobre esa página renderizada con fitz (sin `pdf2image`). Si Tesseract no está disponible, MUST conservar el texto fitz original sin lanzar excepción. El corte temprano de PDE existente MUST mantenerse intacto durante el OCR.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| PDF digital | página con texto > 50 chars | `extraer_texto_pdf()` | devuelve texto fitz; OCR nunca se invoca |
| PDF escaneado + Tesseract instalado | página con texto ≤ 50 chars | `extraer_texto_pdf()` | se invoca OCR con idioma y escala configurados; devuelve texto OCR |
| PDF escaneado + Tesseract ausente | página ≤ 50 chars, binary no existe en disco | `extraer_texto_pdf()` | log warning; devuelve texto fitz original (posiblemente `""`); sin excepción |
| PDF mixto (digital + escaneado) | páginas con y sin texto | `extraer_texto_pdf()` | páginas digitales usan fitz; solo las páginas cortas pasan por OCR |
| PDE con datos completos | marcadores PDE detectados en página N | OCR en curso | corte temprano se aplica igual; no se procesan páginas restantes |

### R2: Configuración vía variables de entorno

Las constantes en `app/constants/auditoria.py` MUST resolver cada valor en orden: variable de entorno → constante default.

| Constante | Env var | Default |
|-----------|---------|---------|
| Ruta binario Tesseract | `TESSERACT_CMD` | `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| Idioma OCR | `TESSERACT_LANG` | `spa` |
| Escala de render | `OCR_SCALE` | `2.0` |

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Sin env vars | ninguna variable seteada | import de constants | se usan los defaults de la tabla |
| Override por env | `TESSERACT_CMD=D:\tools\tesseract.exe` seteada | import de constants | se usa la ruta del env, no el default |
| Override parcial | solo `TESSERACT_LANG=eng` seteada | import de constants | idioma=`eng`; cmd y escala usan defaults |

### R3: Fallback graceful cuando Tesseract no está disponible

Si `TESSERACT_CMD` no existe en disco, el sistema MUST loguear un warning con mensaje claro (incluyendo la ruta configurada), MUST saltear el OCR y MUST devolver el texto fitz como hoy. MUST NOT lanzar excepción ni interrumpir el procesamiento del PDF.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Binary inexistente | ruta configurada no existe en disco | `extraer_texto_pdf()` con PDF escaneado | retorna texto fitz; warning en nivel WARNING; cero excepciones propagadas |
| Auditoría batch sin Tesseract | 10 PDFs escaneados, binary ausente | corrida batch | los 10 se procesan sin crash; cada uno devuelve su texto fitz |

### R4: Rendimiento

OCR SHOULD ejecutarse solo en páginas cuyo texto fitz sea ≤ 50 caracteres (evaluación por página, no global). El corte temprano de PDE MUST preservarse. Para v1 MAY omitirse timeout por página; el volumen acotado por el corte temprano limita el costo.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| PDF digital multipágina | 10 páginas, todas > 50 chars | `extraer_texto_pdf()` | 0 llamadas a OCR |
| PDE escaneado | datos PDE completos tras página 2 con OCR | `extraer_texto_pdf(tipo="PDE")` | OCR solo en páginas procesadas hasta el corte |

### R5: Cobertura de tests

El test `test_no_pytesseract_import` MUST ser reemplazado por un test que verifique que OCR se intenta cuando Tesseract está disponible. MUST agregarse un test de fallback graceful cuando el binary no existe. Todos los tests existentes de PDF digital MUST seguir pasando sin modificación.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| OCR invocado | `os.path.exists` → True, `image_to_string` mockeado | test con PDF escaneado | se llama a `image_to_string` con el idioma configurado |
| Fallback ausente | `os.path.exists` → False | test con PDF escaneado | warning logueado; retorna texto fitz; sin excepción |
| Regresión digital | suite existente | `pytest` completo | tests de PDF digital pasan sin cambios |

## Acceptance Criteria

- [ ] PDF escaneado + Tesseract instalado → texto vía OCR
- [ ] PDF escaneado + Tesseract ausente → texto fitz + log warning, sin crash
- [ ] PDF digital → fast path intacto, OCR nunca invocado
- [ ] Constantes resuelven env var → default en los 3 casos
- [ ] Corte temprano PDE funciona igual con OCR activo
- [ ] Suite `pytest` completa en verde
