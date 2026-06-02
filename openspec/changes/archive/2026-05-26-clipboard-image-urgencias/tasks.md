# Tasks: Clipboard Image Paste Fix (Control de Novedades)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 15–20 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Fix all 3 paste handlers | PR 1 (single) | Self-contained, < 20 lines changed |

## Phase 1: Core Fixes

- [x] 1.1 Global handler carga path (L1552–L1572): add `e.preventDefault()`, reverse loop so last image wins
- [x] 1.2 Global handler individual path (L1578–L1584): remove `break` so `imageFile` overwrites to end — last clipboard match wins
- [x] 1.3 Textarea handler (L1814–L1832): remove unconditional `preventDefault`, extract image without blocking text paste
- [x] 1.4 Global handler TEXTAREA guard (L1576–L1581): if active element is textarea/input (not carga), let browser handle paste naturally

## Phase 2: Testing

- [x] 2.1 **Paste text from Excel in carga textarea** → text appears, image also captured if present
- [x] 2.2 **Paste image in carga textarea** → image captured, no text interference
- [x] 2.3 **Paste in description float** → text pastes normally, no image upload
- [x] 2.4 **Paste image on error modal** → single image upload
- [x] 2.5 **Paste image in carga step 2** → auto-adds image

## Phase 3: Verification

- [ ] 3.1 Confirm no regression in carga masiva paste path with modal closed
- [ ] 3.2 Confirm no regression in individual error edit paste path
- [ ] 3.3 Run full app smoke test: upload, export, download
