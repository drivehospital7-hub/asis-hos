"""Static assertions on the JS embedded in control_errores.html.

Strict TDD — these tests describe the facturador-attachments UI behavior
(FA-2/FA-3/FA-4/FA-5, M-1) by asserting on the template SOURCE. They FAIL
(RED) against the current template, which has no currentImageScope, no
scoped modal URLs, no eye icon in the facturador editor, no scoped paste
target and no facturador badge.

E2E layer is not available (no browser runner), so this static-assert layer
is the designed verification for template JS (design "Testing Strategy").

NOTE: some asserts are approval-style (they document behavior that already
exists: the textarea guard, the _canWrite gating, the count>=3 dropzone
check) — they protect against regression while the NEW scoped asserts fail
RED first.
"""

from pathlib import Path

import pytest

TEMPLATE = (
    Path(__file__).resolve().parent.parent.parent
    / "app" / "templates" / "control_errores.html"
)
HTML = TEMPLATE.read_text(encoding="utf-8")

# Regiones de las dos funciones de renderizado (badges en AMBAS, FA-5)
_RENDER_TABLE_IDX = HTML.index("function renderTable()")
_RENDER_FILTERED_IDX = HTML.index("function renderFilteredTable(errores)")
RENDER_TABLE_REGION = HTML[_RENDER_TABLE_IDX:_RENDER_FILTERED_IDX]
RENDER_FILTERED_REGION = HTML[_RENDER_FILTERED_IDX:]

# Región del modal de imágenes (scope, dropzone, _canWrite, paste)
_MODAL_IDX = HTML.index("// ====== MODAL IMÁGENES ======")
MODAL_REGION = HTML[_MODAL_IDX:]


class TestModalScope:
    """M-1/D4: modal parametrizado por scope ("" observación | facturador)."""

    def test_current_image_scope_variable_exists(self):
        """currentImageScope guarda el scope del modal abierto."""
        assert "let currentImageScope = '';" in MODAL_REGION

    def test_open_image_modal_accepts_scope_param(self):
        """openImageModal(errorId, scope='') — default "" = observación."""
        assert "async function openImageModal(errorId, scope = '')" in MODAL_REGION

    def test_modal_fetch_uses_scoped_url(self):
        """El GET del modal incluye ?scope= cuando hay scope."""
        assert "`/api/control-errores/${errorId}/imagenes${scopeQuery}`" in MODAL_REGION


class TestEyeIconFacturadorEditor:
    """FA-3/D5: ojo dentro del editor facturador: save-then-open scoped."""

    def test_eye_onclick_saves_then_opens_scoped(self):
        """El ojo llama saveFacturadorEditor(id) y luego openImageModal(id,'facturador')."""
        assert (
            "event.stopPropagation(); saveFacturadorEditor('${id}'); "
            "openImageModal('${id}','facturador')"
        ) in HTML

    def test_eye_onclick_stops_propagation(self):
        """stopPropagation evita el click-outside double-save (R5)."""
        assert 'onclick="event.stopPropagation(); saveFacturadorEditor' in HTML


class TestPasteTarget:
    """FA-2: el paste apunta al scope del modal abierto o del editor."""

    def test_paste_uses_current_image_scope(self):
        """Modal abierto → {id, scope: currentImageScope}."""
        assert "scope: currentImageScope" in MODAL_REGION

    def test_paste_falls_back_to_editor_record_scope(self):
        """Sin modal → editor: cell '' (observación) | facturador editor 'facturador'."""
        assert "scope: currentCell ? '' : 'facturador'" in MODAL_REGION

    def test_textarea_guard_unchanged(self):
        """El guard de textarea/input (t:1694) NO se toca: pegar texto sigue default."""
        assert (
            "if (activeEl && (activeEl.tagName === 'TEXTAREA' || "
            "activeEl.tagName === 'INPUT')) {"
        ) in HTML


class TestBadgesAmbosRender:
    """FA-5/D6: badge de count en renderTable Y renderFilteredTable."""

    def test_badge_en_render_table(self):
        """renderTable muestra el badge facturador."""
        assert 'class="facturador-badge"' in RENDER_TABLE_REGION
        assert "imagenes_facturador_count" in RENDER_TABLE_REGION

    def test_badge_en_render_filtered_table(self):
        """renderFilteredTable también muestra el badge facturador."""
        assert 'class="facturador-badge"' in RENDER_FILTERED_REGION
        assert "imagenes_facturador_count" in RENDER_FILTERED_REGION

    def test_badge_en_ambos_render_paths(self):
        """El badge aparece en AMBOS paths (>= 2 ocurrencias totales)."""
        assert HTML.count('class="facturador-badge"') >= 2


class TestReadOnlyGating:
    """FA-4/FA-5: dropzone y delete gated por _canWrite; archivos visibles."""

    def test_dropzone_hidden_at_max_count(self):
        """Dropzone se oculta cuando el count del scope llega a 3."""
        assert "result.data.count >= 3" in MODAL_REGION

    def test_dropzone_gated_by_can_write(self):
        """Sin _canWrite → dropzone oculto (solo visualización)."""
        assert "if (!window._canWrite) {" in MODAL_REGION
        assert "dropzone.style.display = 'none';" in MODAL_REGION

    def test_delete_button_gated_by_can_write(self):
        """Botón delete condicionado a _canWrite."""
        assert "window._canWrite ? `<button class=\"modal-delete-img\"" in MODAL_REGION

    def test_files_visible_sin_permiso(self):
        """Los archivos se renderizan siempre (no dependen de _canWrite)."""
        assert "result.data.imagenes.map(filename => {" in MODAL_REGION