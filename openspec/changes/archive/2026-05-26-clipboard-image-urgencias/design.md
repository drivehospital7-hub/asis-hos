# Design: Clipboard Image Paste Fix (Control de Novedades)

## Technical Approach

Three localized JS edits in `app/templates/control_errores.html`. Frontend-only — no changes to routes, services, or storage. Each fix targets one root cause: event bubbling, forward iteration, and missing `preventDefault`.

## Architecture Decisions

### Decision 1: stopPropagation over removing the global check

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `e.stopPropagation()` in textarea handler | Prevents bubbling to `document`. Targeted, one-liner. | ✅ Chosen |
| Remove the carga path from global handler | More invasive, risks breaking individual paste flow | Rejected |
| Guard flag (`isCargaPaste`) | Stateful, easy to forget reset | Rejected |

### Decision 2: Overwrite (no break) for individual paste path

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Remove `break`, let `imageFile` overwrite till end | Clean diff, works with existing `for...of` | ✅ Chosen |
| Reverse indexed loop | More code, no benefit over overwrite | Rejected |

### Decision 3: No backend dedup

The backend (`guardar_imagen`) saves every POST as a new file. Adding dedup on the backend would mask the frontend bug and create coupling. Fix the source — frontend.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/templates/control_errores.html` | Modify | 3 fix regions: L1552–L1572, L1578–L1584, L1808–L1824 |

No other files touched.

## Exact Code Changes

### Change 1 — Global handler carga path (L1552–L1572)

Add `e.preventDefault()` and reverse the iteration so the **last** `image/*` match wins (most recent clipboard item).

**Before:**
```js
if (!document.getElementById('cargaStep2').classList.contains('hidden')) {
    var clipItems = e.clipboardData?.items;
    if (clipItems) {
      for (var idx = 0; idx < clipItems.length; idx++) {
        if (clipItems[idx].type.startsWith('image/')) {
          var file = clipItems[idx].getAsFile();
          if (file) {
            setTimeout(function() {
              if (cargaImages.length >= 3) return;
              addCargaImageFile(file);
              renderCargaThumbs();
            }, 100);
          }
          break;       // ← picks FIRST (oldest)
        }
      }
    }
  }
```

**After:**
```js
e.preventDefault();  // ← NEW: suppress browser default
if (!document.getElementById('cargaStep2').classList.contains('hidden')) {
    var clipItems = e.clipboardData?.items;
    if (clipItems) {
      for (var idx = clipItems.length - 1; idx >= 0; idx--) {  // ← REVERSE
        if (clipItems[idx].type.startsWith('image/')) {
          var file = clipItems[idx].getAsFile();
          if (file) {
            setTimeout(function() {
              if (cargaImages.length >= 3) return;
              addCargaImageFile(file);
              renderCargaThumbs();
            }, 100);
          }
          break;       // ← now picks LAST (most recent)
        }
      }
    }
  }
```

### Change 2 — Global handler individual paste path (L1578–L1584)

Remove the `break` so `imageFile` keeps overwriting — the last match wins.

**Before:**
```js
let imageFile = null;
for (const item of items) {
  if (item.type.startsWith('image/')) {
    imageFile = item.getAsFile();
    break;  // ← picks first
  }
}
```

**After:**
```js
let imageFile = null;
for (const item of items) {
  if (item.type.startsWith('image/')) {
    imageFile = item.getAsFile();  // ← last match wins
  }
}
```

### Change 3 — Textarea handler (L1808–L1824)

Add `e.preventDefault()` + `e.stopPropagation()` and reverse iteration.

**Before:**
```js
document.getElementById('cargaTextarea').addEventListener('paste', function(e) {
    if (cargaImages.length >= 3) return;
    var items = e.clipboardData?.items;
    if (items) {
      for (var idx = 0; idx < items.length; idx++) {
        if (items[idx].type.startsWith('image/')) {
          var file = items[idx].getAsFile();
          if (file) {
            preguntarImagenCarga(file);
          }
          break;
        }
      }
    }
  });
```

**After:**
```js
document.getElementById('cargaTextarea').addEventListener('paste', function(e) {
    e.preventDefault();      // ← NEW: suppress text insertion
    e.stopPropagation();     // ← NEW: prevent bubble to global handler
    if (cargaImages.length >= 3) return;
    var items = e.clipboardData?.items;
    if (items) {
      for (var idx = items.length - 1; idx >= 0; idx--) {  // ← REVERSE
        if (items[idx].type.startsWith('image/')) {
          var file = items[idx].getAsFile();
          if (file) {
            preguntarImagenCarga(file);
          }
          break;  // ← now picks LAST
        }
      }
    }
  });
```

## Data Flow

```
User paste (Ctrl+V)
    │
    ├─► Textarea handler (L1808)
    │   ├─► e.preventDefault()      → blocks browser text insertion
    │   ├─► e.stopPropagation()     → blocks bubble to document
    │   └─► REVERSE loop → last image → preguntarImagenCarga()
    │
    └─► Global handler (L1550) fires only if NOT pasting in textarea
        ├─► carga path (modal+step2): e.preventDefault() + REVERSE loop
        └─► individual path: no break → last match overwrites
```

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Manual | Double upload | Paste in carga textarea → verify single thumb |
| Manual | Image order | Paste with multiple `image/*` formats → verify most recent |
| Manual | Text insertion | Paste image → verify no text appears in textarea |
| Manual | Individual error paste | Paste on an open error modal → verify single image upload |
| Manual | Cross-browser | Chrome, Edge, Firefox |

## Open Questions

None — all decisions resolved. Ready for task planning.
