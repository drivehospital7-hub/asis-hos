"""Static assertions on the JS embedded in control_errores.html.

Strict TDD — these tests describe the facturador-editor embedded-attachments
UI behavior (FE-1..FE-4, MOD-1, threat matrix D9) by asserting on the template
SOURCE. They FAIL (RED) against the current template, which still renders the
eye-icon bridge inside the facturador editor and has no embedded panel, no
540px sizing, no keep-open lifecycle and no inline paste refresh.

E2E layer is not available (no browser runner), so this static-assert layer
is the designed verification for template JS (design "Testing Strategy").

NOTE: some asserts are approval-style (they document behavior that already
exists and must survive the rework: the obs-cell eye in BOTH render paths,
the modal scope params, the paste target resolution, the textarea guard,
the modal `_canWrite` gating, the facturador badge) — they protect against
regression while the NEW embedded-panel asserts fail RED first.
"""

from pathlib import Path

import pytest

TEMPLATE = (
    Path(__file__).resolve().parent.parent.parent
    / "app" / "templates" / "control_errores.html"
)
HTML = TEMPLATE.read_text(encoding="utf-8")

CSS = (
    Path(__file__).resolve().parent.parent.parent
    / "app" / "static" / "css" / "legacy" / "control_errores.css"
).read_text(encoding="utf-8")

# Regiones de las dos funciones de renderizado (ojo obs en AMBAS, MOD-1)
_RENDER_TABLE_IDX = HTML.index("function renderTable()")
_RENDER_FILTERED_IDX = HTML.index("function renderFilteredTable(errores)")
RENDER_TABLE_REGION = HTML[_RENDER_TABLE_IDX:_RENDER_FILTERED_IDX]
RENDER_FILTERED_REGION = HTML[_RENDER_FILTERED_IDX:]

# Región del modal de imágenes (scope, dropzone, _canWrite, paste target)
_MODAL_IDX = HTML.index("// ====== MODAL IMÁGENES ======")
MODAL_REGION = HTML[_MODAL_IDX:]

# Editor facturador: openFacturadorEditor → saveFacturadorEditor
# (incluye impl, el listener doc-level único y los flags D4/D5)
_EDITOR_IDX = HTML.index("function openFacturadorEditor(")
_SAVE_FACT_IDX = HTML.index("function saveFacturadorEditor(")
EDITOR_REGION = HTML[_EDITOR_IDX:_SAVE_FACT_IDX]

# Impl del editor facturador: openFacturadorEditorImpl → saveFacturadorEditor
_IMPL_IDX = HTML.index("function openFacturadorEditorImpl(")
IMPL_REGION = HTML[_IMPL_IDX:_SAVE_FACT_IDX]

# Funciones del panel embebido: saveFacturadorEditor → EDITOR GLOBAL
_EDITOR_GLOBAL_IDX = HTML.index("// ====== EDITOR GLOBAL ======")
PANEL_REGION = HTML[_SAVE_FACT_IDX:_EDITOR_GLOBAL_IDX]

# Cell-edit sizing: openEditor → closeEditor (rect-derived, FE-3)
_OPEN_EDITOR_IDX = HTML.index("function openEditor(")
_CLOSE_EDITOR_IDX = HTML.index("function closeEditor()")
OPEN_EDITOR_REGION = HTML[_OPEN_EDITOR_IDX:_CLOSE_EDITOR_IDX]

# closeEditor → listener global de Enter (reset de tamaño, FE-3)
_ENTER_KEY_IDX = HTML.index("// Guardar al presionar Enter")
CLOSE_EDITOR_REGION = HTML[_CLOSE_EDITOR_IDX:_ENTER_KEY_IDX]

# Paste handler → CARGA MASIVA (guards + inline refresh, FE-2/D6)
_PASTE_IDX = HTML.index("document.addEventListener('paste'")
_CARGA_IDX = HTML.index("// ====== CARGA MASIVA ======")
PASTE_REGION = HTML[_PASTE_IDX:_CARGA_IDX]

# Regiones de save: saveFacturadorEditor (cierre) vs keep-open, por función
_KEEPOPEN_IDX = PANEL_REGION.index("function saveFacturadorEditorKeepOpen(")
SAVE_CLOSE_REGION = PANEL_REGION[:_KEEPOPEN_IDX]
SAVE_KEEPOPEN_REGION = PANEL_REGION[_KEEPOPEN_IDX:]


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


class TestEyeBridgeRemoved:
    """MOD-1: el puente ojo dentro del editor facturador desaparece.

    El ojo de la celda de observación (scope '') se preserva en AMBOS render
    paths; el editor facturador NUNCA abre #image-modal (facturador scope).
    """

    def test_editor_eye_button_absent(self):
        """No existe editor-eye-btn dentro del editor facturador."""
        assert "editor-eye-btn" not in EDITOR_REGION

    def test_editor_no_save_then_open_scoped(self):
        """El editor no llama el secuencia save-then-open con scope facturador."""
        assert "openImageModal('${id}','facturador')" not in EDITOR_REGION

    def test_facturador_impl_never_opens_image_modal(self):
        """openFacturadorEditorImpl no contiene ninguna llamada openImageModal."""
        assert "openImageModal" not in IMPL_REGION

    def test_obs_eye_present_in_render_table(self):
        """renderTable conserva el ojo obs-cell (scope '')."""
        assert "openImageModal('${e.id}')" in RENDER_TABLE_REGION

    def test_obs_eye_present_in_render_filtered_table(self):
        """renderFilteredTable conserva el ojo obs-cell (scope '')."""
        assert "openImageModal('${e.id}')" in RENDER_FILTERED_REGION


class TestEmbeddedPanel:
    """FE-1/D2: panel de adjuntos embebido con render compartido."""

    def test_render_facturador_attachments_defined(self):
        """El renderer compartido del panel existe."""
        assert "async function renderFacturadorAttachments(" in PANEL_REGION

    def test_impl_calls_render_facturador_attachments(self):
        """El impl llama al renderer (un solo punto de render, FE-3)."""
        assert "renderFacturadorAttachments(errorId)" in IMPL_REGION

    def test_panel_shell_in_impl(self):
        """El impl renderiza el shell #facturador-attachments."""
        assert 'id="facturador-attachments"' in IMPL_REGION

    def test_panel_markup_strings(self):
        """El panel usa clases editor-dropzone / editor-thumb / editor-count."""
        assert 'class="editor-dropzone"' in PANEL_REGION
        assert 'class="editor-thumb"' in PANEL_REGION
        assert 'class="editor-count"' in PANEL_REGION

    def test_panel_count_markup(self):
        """El panel renderiza el count del scope y lo expone para el paste."""
        assert "result.data.count" in PANEL_REGION
        assert "container.dataset.count = count" in PANEL_REGION


class TestCanFacturadorAttachFlag:
    """Regla de negocio: flag server-rendered para adjuntos de facturador.

    ``window._canFacturadorAttach`` = admin (*) O (control_urgencias SIN
    control_urgencias:write). Se usa SOLO en el panel de adjuntos facturador;
    el resto sigue con ``_canWrite``.
    """

    FLAG = (
        "window._canFacturadorAttach = {{ 'true' if '*' in session.get('permisos', [])"
        " or ('control_urgencias' in session.get('permisos', []) and "
        "'control_urgencias:write' not in session.get('permisos', [])) else 'false' }};"
    )

    def test_flag_is_server_rendered(self):
        """El flag facturador se renderiza desde el server."""
        assert "window._canFacturadorAttach =" in HTML

    def test_flag_uses_exact_rule_expression(self):
        """La expresión del flag es: admin O (control_urgencias SIN :write)."""
        assert (
            "'control_urgencias' in session.get('permisos', []) and "
            "'control_urgencias:write' not in session.get('permisos', [])"
        ) in HTML

    def test_can_write_flag_unchanged(self):
        """El flag _canWrite original se conserva."""
        assert "window._canWrite =" in HTML

    def test_facturador_panel_uses_facturador_flag_not_can_write(self):
        """El panel facturador usa _canFacturadorAttach, NO _canWrite."""
        assert "window._canFacturadorAttach" in PANEL_REGION
        assert "window._canWrite" not in PANEL_REGION

    def test_observacion_modal_keeps_can_write(self):
        """El modal de observación sigue usando _canWrite (sin cambios)."""
        assert "if (!window._canWrite) {" in MODAL_REGION
        assert "dropzone.style.display = 'none';" in MODAL_REGION

    def test_observacion_modal_delete_keeps_can_write(self):
        """Botón delete del modal observación condicionado a _canWrite."""
        assert "window._canWrite ? `<button class=\"modal-delete-img\"" in MODAL_REGION


class TestPanelGating:
    """FE-1/D8: dropzone y delete gated por _canFacturadorAttach; archivos siempre visibles."""

    def test_upload_and_delete_gated_by_can_facturador_attach(self):
        """uploadFacturadorImages y deleteFacturadorImage arrancan con el guard facturador."""
        assert PANEL_REGION.count("if (!window._canFacturadorAttach) return;") >= 2

    def test_upload_and_delete_no_longer_gated_by_can_write(self):
        """Los guards de subir/borrar facturador NO usan _canWrite (regla de negocio)."""
        assert "if (!window._canWrite) return;" not in PANEL_REGION

    def test_delete_button_gated_by_can_facturador_attach(self):
        """El botón delete del panel se condiciona a _canFacturadorAttach."""
        assert 'window._canFacturadorAttach ? `<button type="button" class="editor-thumb-delete"' in PANEL_REGION

    def test_dropzone_hidden_at_max_count(self):
        """Dropzone del panel solo con permiso y con cupo (count < 3)."""
        assert "window._canFacturadorAttach && count < 3" in PANEL_REGION

    def test_files_render_unconditionally(self):
        """Los archivos se renderizan siempre (no dependen de _canFacturadorAttach)."""
        assert "result.data.imagenes.map(filename => {" in PANEL_REGION


class TestFacturadorSizing:
    """FE-3/D7: 540px en modo facturador; reset en closeEditor; cell-edit intacto."""

    def test_facturador_width_constant_540(self):
        """La constante de ancho facturador es 540 (rango 520-560)."""
        assert "const FACTURADOR_EDITOR_WIDTH = 540;" in IMPL_REGION

    def test_impl_uses_540_width(self):
        """El impl aplica la constante como width del editor."""
        assert "editor.style.width = FACTURADOR_EDITOR_WIDTH + 'px'" in IMPL_REGION

    def test_impl_content_height(self):
        """Altura content-driven: sin height fijo y SIN min-height forzado."""
        assert "editor.style.height = ''" in IMPL_REGION
        assert "editor.style.minHeight = '320px'" not in IMPL_REGION

    def test_close_editor_resets_width(self):
        """closeEditor limpia el width ampliado (no filtra a cell-edit)."""
        assert "editor.style.width = ''" in CLOSE_EDITOR_REGION

    def test_open_editor_keeps_rect_width(self):
        """openEditor mantiene el sizing por rect de la celda."""
        assert "editor.style.width = rect.width + 'px'" in OPEN_EDITOR_REGION


class TestPasteTarget:
    """FE-2: el paste apunta al scope del modal abierto o del editor."""

    def test_paste_uses_current_image_scope(self):
        """Modal abierto → {id, scope: currentImageScope}."""
        assert "scope: currentImageScope" in PASTE_REGION

    def test_paste_falls_back_to_editor_record_scope(self):
        """Sin modal → editor: cell '' (observación) | facturador editor 'facturador'."""
        assert "scope: currentCell ? '' : 'facturador'" in PASTE_REGION

    def test_textarea_guard_unchanged(self):
        """El guard de textarea/input NO se toca: pegar texto sigue default."""
        assert (
            "if (activeEl && (activeEl.tagName === 'TEXTAREA' || "
            "activeEl.tagName === 'INPUT')) {"
        ) in HTML


class TestPasteFacturadorBranch:
    """FE-2/D6: guard por scope + refresh inline en scope facturador."""

    def test_paste_guard_is_scope_aware(self):
        """El paste chequea _canFacturadorAttach para facturador y _canWrite para observación."""
        assert "target.scope === 'facturador'" in PASTE_REGION
        assert "window._canFacturadorAttach" in PASTE_REGION
        assert "window._canWrite" in PASTE_REGION

    def test_paste_facturador_uses_facturador_attach_flag(self):
        """Scope facturador → se usa _canFacturadorAttach (no _canWrite)."""
        assert "target.scope === 'facturador'\n      ? window._canFacturadorAttach\n      : window._canWrite" in PASTE_REGION

    def test_paste_max_three_guard(self):
        """Cupo max-3 en scope facturador → alert y skip."""
        assert "currentCount >= 3" in PASTE_REGION
        assert "Modal.alert('Máximo 3" in PASTE_REGION

    def test_paste_facturador_inline_refresh(self):
        """Éxito + scope facturador → render inline del panel."""
        assert "if (target.scope === 'facturador') {" in PASTE_REGION
        assert "renderFacturadorAttachments(target.id)" in PASTE_REGION

    def test_paste_no_close_editor(self):
        """El paste facturador NUNCA cierra el editor (textarea intacto)."""
        assert "closeEditor(" not in PASTE_REGION


class TestDeleteKeepOpen:
    """FE-4/D4/D5: delete con confirm y overlay → save idempotente sin cerrar."""

    def test_delete_sets_busy_flag(self):
        """deleteFacturadorImage marca _facturadorModalBusy antes del confirm."""
        assert "_facturadorModalBusy = true" in PANEL_REGION

    def test_delete_confirms_before_delete(self):
        """deleteFacturadorImage pide confirm antes del DELETE."""
        assert "await Modal.confirm('¿Eliminar imagen facturador?')" in PANEL_REGION

    def test_delete_refreshes_panel_and_table(self):
        """Éxito → refresh del panel embebido + tabla."""
        assert "renderFacturadorAttachments(errorId)" in PANEL_REGION
        assert "loadErrores()" in PANEL_REGION

    def test_delete_resets_busy_flag(self):
        """El flag busy se libera en finally (siempre)."""
        assert "_facturadorModalBusy = false" in PANEL_REGION

    def test_doc_click_keep_open_handler(self):
        """Listener doc-level único llama saveFacturadorEditorKeepOpen."""
        assert "saveFacturadorEditorKeepOpen(currentEditId)" in EDITOR_REGION

    def test_overlay_and_busy_branches(self):
        """Click en overlay de confirm o con busy → keep-open (no cierra)."""
        assert ".confirm-overlay" in EDITOR_REGION
        assert "_facturadorModalBusy" in EDITOR_REGION

    def test_keep_open_idempotent(self):
        """keepOpen compara contra _facturadorLastSavedText (PUT único)."""
        assert "function saveFacturadorEditorKeepOpen(" in PANEL_REGION
        assert "newValue === _facturadorLastSavedText" in PANEL_REGION


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
    """FA-4/FA-5: modal — dropzone y delete gated por _canWrite; archivos visibles."""

    def test_dropzone_hidden_at_max_count(self):
        """Dropzone del modal se oculta cuando el count del scope llega a 3."""
        assert "result.data.count >= 3" in MODAL_REGION

    def test_dropzone_gated_by_can_write(self):
        """Sin _canWrite → dropzone del modal oculto (solo visualización)."""
        assert "if (!window._canWrite) {" in MODAL_REGION
        assert "dropzone.style.display = 'none';" in MODAL_REGION

    def test_delete_button_gated_by_can_write(self):
        """Botón delete del modal condicionado a _canWrite."""
        assert "window._canWrite ? `<button class=\"modal-delete-img\"" in MODAL_REGION

    def test_files_visible_sin_permiso(self):
        """Los archivos del modal se renderizan siempre."""
        assert "result.data.imagenes.map(filename => {" in MODAL_REGION


class TestThreatInlineJs:
    """Threat matrix D9: sin inyección inline-JS con filename crudo en el panel."""

    def test_panel_escapes_filenames(self):
        """Labels del panel escapan el filename (escapeHtml)."""
        assert "escapeHtml(filename)" in PANEL_REGION

    def test_panel_encodes_urls(self):
        """URLs del panel codifican el filename (encodeURIComponent)."""
        assert "encodeURIComponent(filename)" in PANEL_REGION

    def test_no_raw_filename_in_inline_onclick(self):
        """No hay onclick inline que interpole el filename crudo (delegación)."""
        assert "deleteFacturadorImage('${id}','${filename}'" not in PANEL_REGION

    def test_delete_delegated_via_data_attribute(self):
        """El delete delegado lee el filename desde data-filename."""
        assert "del.dataset.filename" in PANEL_REGION

    def test_image_view_delegated_via_data_attribute(self):
        """El click sobre un thumb de imagen delega con data-filename."""
        assert "img.dataset.filename" in PANEL_REGION


class TestSaveFacturadorResilience:
    """R2: cache/lastUpdate/guard SOLO en éxito; fallo revierte y avisa."""

    def test_close_save_validates_status_and_applies_cache_after(self):
        """saveFacturadorEditor: res.ok chequeado y optimista aplicado después."""
        assert "if (!res.ok) throw new Error('HTTP ' + res.status);" in SAVE_CLOSE_REGION
        ok = SAVE_CLOSE_REGION.index("if (!res.ok) throw new Error('HTTP ' + res.status);")
        assert SAVE_CLOSE_REGION.index("error.observacion_facturador = newValue;") > ok
        assert SAVE_CLOSE_REGION.index("lastUpdate = new Date().toISOString();") > ok

    def test_close_save_rolls_back_and_toast_on_failure(self):
        """saveFacturadorEditor: fallo revierte cache/botón y avisa con toast."""
        assert "error.observacion_facturador = originalValue;" in SAVE_CLOSE_REGION
        assert "_updateFacturadorNoteButton(saveId, originalValue);" in SAVE_CLOSE_REGION
        assert "showToast('No se guardó la observación del facturador', 'error')" in SAVE_CLOSE_REGION

    def test_note_button_uses_css_green_no_inline_amber_override(self):
        """El lápiz con nota usa el verde del CSS .has-note; sin override ámbar inline."""
        assert "btn.classList.add('has-note');" in SAVE_CLOSE_REGION
        assert "btn.style.setProperty('color', '#f59e0b', 'important')" not in HTML
        assert "btn.style.setProperty('color', '#64748b', 'important')" not in HTML

    def test_keep_open_validates_status_and_applies_cache_after(self):
        """keep-open: res.ok chequeado y optimista/guard aplicados después del PUT."""
        assert "if (!res.ok) {" in SAVE_KEEPOPEN_REGION
        ok = SAVE_KEEPOPEN_REGION.index("if (!res.ok) {")
        assert SAVE_KEEPOPEN_REGION.index("error.observacion_facturador = newValue;") > ok
        assert SAVE_KEEPOPEN_REGION.index("_facturadorLastSavedText = newValue;") > SAVE_KEEPOPEN_REGION.index("await fetch(")

    def test_keep_open_failure_rolls_back_and_toast(self):
        """keep-open: fallo revierte cache y avisa SIN cerrar el editor."""
        assert "error.observacion_facturador = originalValue;" in SAVE_KEEPOPEN_REGION
        assert "showToast('No se guardó la observación del facturador', 'error')" in SAVE_KEEPOPEN_REGION


class TestDeleteDoesNotFreezeEditor:
    """R3: borrar la fila con editor abierto no congela la página."""

    def test_delete_and_reload_close_editor_when_row_gone(self):
        """deleteError, loadErrores y los saves cierran el editor si la fila desapareció."""
        assert "if (currentEditId === id) closeEditor();" in HTML
        assert "!cachedErrores.some(e => e.id === currentEditId)" in HTML
        assert "if (!error) { closeEditor(); return; }" in SAVE_CLOSE_REGION
        assert "if (!error) { closeEditor(); return; }" in SAVE_KEEPOPEN_REGION


class TestKeydownListenerCleanup:
    """R4: el listener per-open se remueve en TODOS los close paths."""

    def test_handler_cleaned_up_in_all_close_paths(self):
        """El handler per-open se guarda, closeEditor lo remueve, Enter/Escape comparten remover."""
        assert "_facturadorKeydownHandler = handleKeydown;" in IMPL_REGION
        assert "_removeFacturadorKeydownListener();" in CLOSE_EDITOR_REGION
        assert IMPL_REGION.count("_removeFacturadorKeydownListener();") >= 2


class TestPasteFacturadorRefresh:
    """R6: el paste facturador refresca tabla/badge y avanza lastUpdate."""

    def test_paste_facturador_refreshes_table_and_advances_last_update(self):
        """Éxito + scope facturador → loadErrores + lastUpdate (badge al día)."""
        fact_idx = PASTE_REGION.index("if (target.scope === 'facturador') {")
        branch = PASTE_REGION[fact_idx:PASTE_REGION.index("} else {", fact_idx)]
        assert "loadErrores()" in branch
        assert "lastUpdate = new Date().toISOString();" in branch
        assert "renderFacturadorAttachments(target.id)" in branch


class TestFacturadorIntegratedColors:
    """FE-5: el panel de adjuntos usa la paleta del modal facturador.

    El modal facturador es superficie amarilla (#fef9c3) con acento ámbar
    (#f59e0b, el mismo del botón de nota). El panel embebido debe compartir
    esos tokens (no el gris #f8fafc ni el verde genérico --primary) para
    pertenecer visualmente al modal. Los colores se declaran como variables
    nombradas (sin magic numbers, convención del proyecto).
    """

    def test_facturador_surface_variable_declared(self):
        """La superficie del modal facturador se declara como variable."""
        assert "--facturador-surface: #fef9c3;" in CSS

    def test_facturador_accent_variable_declared(self):
        """El acento del modal facturador se declara como variable (#f59e0b)."""
        assert "--facturador-accent: #f59e0b;" in CSS

    def test_panel_uses_surface_variable(self):
        """.facturador-attachments usa la superficie facturador como fondo."""
        start = CSS.index(".facturador-attachments {")
        end = CSS.index("}\n.editor-count", start)
        block = CSS[start:end]
        assert "background: var(--facturador-surface);" in block

    def test_panel_keeps_modal_border(self):
        """.facturador-attachments mantiene el borde del modal (#e2e8f0)."""
        assert "--facturador-border: #e2e8f0;" in CSS
        start = CSS.index(".facturador-attachments {")
        end = CSS.index("}\n.editor-count", start)
        block = CSS[start:end]
        assert "border-top: 1px solid var(--facturador-border);" in block

    def test_dropzone_hover_uses_facturador_accent(self):
        """.editor-dropzone:hover/.dragover usan el acento facturador, no --primary."""
        start = CSS.index(".editor-dropzone:hover,")
        end = CSS.index("}\n.editor-dropzone-text", start)
        block = CSS[start:end]
        assert "border-color: var(--facturador-accent);" in block
        assert "var(--primary)" not in block

    def test_dropzone_base_uses_surface(self):
        """.editor-dropzone base comparte la superficie facturador."""
        start = CSS.index(".editor-dropzone {")
        end = CSS.index("}\n.editor-dropzone:hover,", start)
        block = CSS[start:end]
        assert "background: var(--facturador-surface);" in block


class TestFacturadorAutoGrow:
    """FE-5: auto-grow del textarea facturador (solo modo facturador).

    El textarea crece al tipear hasta FACTURADOR_TEXTAREA_MAX_HEIGHT (constante
    nombrada, sin magic numbers) reseteando height a auto y fijando
    min(scrollHeight, MAX). El handler se liga SOLO al textarea facturador
    (openFacturadorEditorImpl), nunca al de cell-edit (openEditor).
    """

    def test_max_height_named_constant(self):
        """La altura máxima es una constante nombrada (~300px)."""
        assert "const FACTURADOR_TEXTAREA_MAX_HEIGHT = 300;" in IMPL_REGION

    def test_impl_binds_input_autogrow(self):
        """openFacturadorEditorImpl liga un listener 'input' de auto-grow."""
        assert "addEventListener('input'" in IMPL_REGION
        assert "FACTURADOR_TEXTAREA_MAX_HEIGHT" in IMPL_REGION

    def test_autogrow_reset_then_min_scroll_height(self):
        """Auto-grow: height a auto y luego min(scrollHeight, MAX)."""
        assert "ta.style.height = 'auto';" in IMPL_REGION
        assert "Math.min(ta.scrollHeight, FACTURADOR_TEXTAREA_MAX_HEIGHT)" in IMPL_REGION

    def test_autogrow_only_in_facturador_impl(self):
        """openEditor (cell-edit) NO liga el auto-grow por input."""
        start = HTML.index("function openEditor(")
        end = HTML.index("function closeEditor(")
        open_editor_region = HTML[start:end]
        assert "FACTURADOR_TEXTAREA_MAX_HEIGHT" not in open_editor_region

    def test_autogrow_preserves_enter_save_and_escape_close(self):
        """El auto-grow no rompe Enter-save ni Escape-close del facturador."""
        assert "if (e.key === 'Enter' && !e.shiftKey)" in IMPL_REGION
        assert "if (e.key === 'Escape')" in IMPL_REGION


class TestFacturadorIntegratedSurface:
    """FE-6: el editor facturador es UNA superficie amarilla, sin hueco blanco.

    El contenedor #global-editor tiene background:#ffffff por defecto (CSS).
    En modo facturador el contenedor debe adoptar la superficie del modal
    (--facturador-surface #fef9c3) para que textarea + panel de adjuntos se
    lean como una sola pieza integrada, sin espacio blanco visible. El modo se
    marca con la clase .facturador-mode (agregada al abrir, removida al cerrar
    para que cell-edit conserve su fondo blanco).
    """

    def test_impl_adds_facturador_mode_class(self):
        """openFacturadorEditorImpl marca el editor con .facturador-mode."""
        assert "editor.classList.add('facturador-mode')" in IMPL_REGION

    def test_close_editor_removes_facturador_mode_class(self):
        """closeEditor remueve .facturador-mode (no filtra a cell-edit)."""
        assert "editor.classList.remove('facturador-mode')" in CLOSE_EDITOR_REGION

    def test_facturador_mode_container_uses_surface(self):
        """#global-editor.facturador-mode usa la superficie facturador de fondo."""
        assert (
            "#global-editor.facturador-mode {"
            "\n  background: var(--facturador-surface);"
            "\n}" in CSS
        )

    def test_container_default_background_still_white(self):
        """El contenedor base conserva fondo blanco (cell-edit, FE-3 intacto)."""
        start = CSS.index("#global-editor {")
        end = CSS.index("}\n\n#global-editor textarea", start)
        block = CSS[start:end]
        assert "background: #ffffff;" in block

    def test_panel_has_no_top_margin_gap(self):
        """.facturador-attachments tiene margin-top cero y solo border-top."""
        start = CSS.index(".facturador-attachments {")
        end = CSS.index("}\n.editor-count", start)
        block = CSS[start:end]
        assert "border-top: 1px solid var(--facturador-border);" in block
        assert "margin-top: 0;" in block
        assert "gap:" not in block

    def test_facturador_textarea_no_bottom_margin(self):
        """El textarea facturador no tiene margin-bottom (contiguo al panel)."""
        textarea_start = IMPL_REGION.index('id="editor-input"')
        textarea_block = IMPL_REGION[textarea_start:]
        assert "margin-bottom" not in textarea_block.split("</textarea>")[0]

    def test_facturador_container_no_padding_void(self):
        """#global-editor.facturador-mode no introduce padding que cree un hueco."""
        assert (
            "#global-editor.facturador-mode {"
            "\n  background: var(--facturador-surface);"
            "\n}" in CSS
        )

    def test_facturador_no_minheight(self):
        """El modo facturador NO fija min-height: la altura es content-driven."""
        assert "editor.style.minHeight = '320px'" not in IMPL_REGION
        assert "editor.style.minHeight =" not in IMPL_REGION

    def test_no_stray_5px_min_height(self):
        """No existe ningún min-height:5px colapsado en el template ni en el CSS."""
        assert "min-height: 5px" not in HTML
        assert "min-height:5px" not in HTML
        assert "min-height: 5px" not in CSS
        assert "min-height:5px" not in CSS

    def test_facturador_editor_has_no_textarea_baseline_gap(self):
        """Textarea y panel quedan contiguos, sin baseline ni whitespace gap."""
        assert (
            "#global-editor.facturador-mode #editor-input {"
            "\n  display: block;"
            "\n}" in CSS
        )
        assert "</textarea><div id=\"facturador-attachments\"" in IMPL_REGION
        panel_start = CSS.index(".facturador-attachments {")
        panel_end = CSS.index("}\n.editor-count", panel_start)
        assert "margin-top: 0;" in CSS[panel_start:panel_end]


class TestFacturadorPanelTypography:
    """FE-7: la tipografía del panel de adjuntos es la MISMA que la de las
    letras de observación del textarea facturador (#editor-input).

    El textarea facturador usa `font:inherit; font-size:13px` (color heredado
    = --foreground, family heredada del body, weight 400, line-height heredada).
    Para que el panel se lea como parte de la misma superficie de observación,
    los textos del panel (.editor-count, .editor-dropzone, .editor-dropzone-text,
    .editor-thumb-link) deben compartir ese color, tamaño 13px, family, weight y
    line-height. El override va SCOPED a #global-editor.facturador-mode para no
    afectar cell-edit (#image-modal / openEditor). Sin magic numbers: el tamaño
    13px se declara como variable nombrada (misma fuente que el textarea).
    """

    def test_observation_font_size_named_variable(self):
        """El tamaño de letra de observación se declara como variable (13px)."""
        assert "--facturador-obs-font-size: 13px;" in CSS

    def test_panel_text_matches_placeholder_muted_color(self):
        """.editor-count / .editor-dropzone / .editor-dropzone-text /
        .editor-thumb-link usan el mismo tono grisáceo/placeholder que la
        observación del facturador. Como no hay regla ::placeholder explícita
        para #editor-input / #global-editor textarea, el panel usa el valor
        muted del proyecto (--muted-foreground), NO el foreground oscuro."""
        start = CSS.index("#global-editor.facturador-mode .editor-count,")
        end = CSS.index("}\n", start)
        panel_block = CSS[start:end]
        assert "color: var(--muted-foreground);" in panel_block
        assert "color: var(--foreground);" not in panel_block

    def test_panel_text_matches_textarea_font_size(self):
        """.editor-count / .editor-dropzone-text heredan 13px de observación."""
        start = CSS.index("#global-editor.facturador-mode")
        end = CSS.index("/* ====== Panel de adjuntos", start)
        scoped_block = CSS[start:end]
        assert "font-size: var(--facturador-obs-font-size);" in scoped_block

    def test_panel_text_matches_textarea_weight_and_line_height(self):
        """El panel comparte el weight (400) y line-height del textarea."""
        start = CSS.index("#global-editor.facturador-mode")
        end = CSS.index("/* ====== Panel de adjuntos", start)
        scoped_block = CSS[start:end]
        assert "font-weight: inherit;" in scoped_block
        assert "line-height: inherit;" in scoped_block

    def test_panel_text_matches_textarea_font_family(self):
        """.editor-count / .editor-dropzone-text heredan la family del body
        (font-family: inherit, igual que font:inherit del textarea)."""
        start = CSS.index("#global-editor.facturador-mode")
        end = CSS.index("/* ====== Panel de adjuntos", start)
        scoped_block = CSS[start:end]
        assert "font-family: inherit;" in scoped_block

    def test_thumb_link_shares_observation_typography(self):
        """.editor-thumb-link comparte size/family de observación (no acento)."""
        start = CSS.index("#global-editor.facturador-mode")
        end = CSS.index("/* ====== Panel de adjuntos", start)
        scoped_block = CSS[start:end]
        assert "font-size: var(--facturador-obs-font-size);" in scoped_block
        assert "color: var(--muted-foreground);" in scoped_block

    def test_cell_edit_typography_untouched(self):
        """El override está scoped a facturador-mode: #image-modal y cell-edit
        (openEditor) no se ven afectados (sin selector global que los pise)."""
        start = CSS.index("#global-editor.facturador-mode")
        end = CSS.index("/* ====== Panel de adjuntos", start)
        scoped_block = CSS[start:end]
        assert "#global-editor.facturador-mode" in scoped_block
        assert "#image-modal" not in scoped_block


class TestFacturadorInstantPanelShell:
    """FE-8: el panel de adjuntos se siente simultáneo con la observación.

    El esqueleto (conteo + dropzone) se renderiza de forma SÍNCRONA apenas se
    abre el editor; renderFacturadorAttachments lo reemplaza con el conteo y
    thumbnails reales cuando llega la respuesta del GET.
    """

    def test_shell_function_defined(self):
        """Existe renderFacturadorAttachmentsShell en el panel embebido."""
        assert "function renderFacturadorAttachmentsShell(errorId)" in PANEL_REGION

    def test_shell_rendered_before_async_fetch(self):
        """El esqueleto se dibuja ANTES del render async de thumbnails."""
        shell_idx = IMPL_REGION.index("renderFacturadorAttachmentsShell(errorId);")
        async_idx = IMPL_REGION.index("renderFacturadorAttachments(errorId);")
        assert shell_idx < async_idx

    def test_shell_shows_placeholder_count(self):
        """El esqueleto muestra el conteo placeholder hasta llegar la respuesta."""
        shell_fn = PANEL_REGION[PANEL_REGION.index("function renderFacturadorAttachmentsShell(errorId)"):]
        assert "Adjuntos facturador (…/3)" in shell_fn

    def test_shell_binds_dropzone_and_gates_by_can_facturador_attach(self):
        """El esqueleto bindea el dropzone y lo muestra solo con _canFacturadorAttach."""
        shell_fn = PANEL_REGION[PANEL_REGION.index("function renderFacturadorAttachmentsShell(errorId)"):]
        assert "_bindFacturadorDropzone(errorId);" in shell_fn
        assert "window._canFacturadorAttach" in shell_fn
        assert "editor-dropzone" in shell_fn


class TestObsEyeAttachmentBadge:
    """FE-9: el ojito de descripción muestra el contador de adjuntos cuando
    tiene archivos (imagenes_count), igual que el lápiz del facturador."""

    OBS_BADGE_TEMPLATE = "${e.imagenes_count > 0 ? `<span class=\"obs-badge\">${e.imagenes_count}</span>` : ''}"

    def test_obs_badge_in_render_table(self):
        """El badge del ojito está en renderTable."""
        assert self.OBS_BADGE_TEMPLATE in RENDER_TABLE_REGION

    def test_obs_badge_in_render_filtered_table(self):
        """El badge del ojito está en renderFilteredTable."""
        assert self.OBS_BADGE_TEMPLATE in RENDER_FILTERED_REGION

    def test_obs_badge_css_defined_with_amber_style(self):
        """El CSS define .obs-img-btn .obs-badge con el mismo estilo ámbar."""
        start = CSS.index(".obs-img-btn .obs-badge {")
        end = CSS.index("}\n", start)
        badge_block = CSS[start:end]
        assert "background: #f59e0b;" in badge_block
        assert "color: #ffffff;" in badge_block
        assert "position: absolute;" in badge_block
