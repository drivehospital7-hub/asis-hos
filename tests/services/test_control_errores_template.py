"""RED/static tests for control_errores.html template (FA-4/FA-9 deltas).

Strict TDD — these assert the frontend contract the template must satisfy:

- ``_canFacturadorAttach`` is true for ``control_urgencias`` WITH or WITHOUT
  ``:write`` (FA-4/D15), so ``:write`` can attach to facturador.
- Both render paths (facturador panel + observación modal) iterate over
  ``{filename, can_delete}`` objects and condition the delete button on the
  per-file ``canDelete`` (FA-9/D16), not the global write flag.
- ``_canWrite`` stays unchanged (observación scope, global write).
"""

from pathlib import Path

TEMPLATE = (
    Path(__file__).resolve().parent.parent.parent
    / "app" / "templates" / "control_errores.html"
)
TEMPLATE_TEXT = TEMPLATE.read_text(encoding="utf-8")


class TestCanFacturadorAttachFlag:
    """FA-4/D15: el flag habilita el dropzone facturador para ambos roles."""

    def test_flag_no_bloquea_write(self):
        """`:write` (además de control_urgencias) habilita _canFacturadorAttach."""
        assert "or 'control_urgencias' in session.get('permisos', [])" in TEMPLATE_TEXT
        # Ya NO debe exigir ausencia de :write para el flag
        assert "control_urgencias:write' not in session.get('permisos', [])" not in TEMPLATE_TEXT

    def test_can_write_sin_cambio(self):
        """_canWrite sigue siendo global (observación) con :write o admin."""
        assert (
            "window._canWrite = {{ 'true' if '*' in session.get('permisos', []) "
            "or 'control_urgencias:write' in session.get('permisos', []) else 'false' }}"
        ) in TEMPLATE_TEXT


class TestFacturadorRenderPath:
    """FA-9: el panel facturador itera {filename, can_delete} y borra por canDelete."""

    def test_map_item_con_can_delete(self):
        """El mapa facturador usa item.filename e item.can_delete."""
        assert "result.data.imagenes.map(item => {" in TEMPLATE_TEXT
        assert "const filename = item.filename;" in TEMPLATE_TEXT
        assert "const canDelete = item.can_delete;" in TEMPLATE_TEXT

    def test_delete_btn_por_can_delete(self):
        """El botón delete facturador se condiciona a canDelete, no al flag global."""
        assert "const deleteBtn = canDelete ?" in TEMPLATE_TEXT
        # Ya NO se usa _canFacturadorAttach para el botón delete por archivo
        assert "window._canFacturadorAttach ? `<button" not in TEMPLATE_TEXT

    def test_dropzone_mantiene_can_facturador_attach(self):
        """El dropzone facturador (ambos roles) usa _canFacturadorAttach y cupo <3."""
        assert (
            "if (window._canFacturadorAttach && count < 3) {" in TEMPLATE_TEXT
        )


class TestModalObservacionRenderPath:
    """FA-9/D16: el modal observación itera {filename, can_delete} por archivo."""

    def test_modal_map_item_con_can_delete(self):
        """El mapa del modal usa item.filename e item.can_delete."""
        assert "result.data.imagenes.map(item => {" in TEMPLATE_TEXT
        assert "const filename = item.filename;" in TEMPLATE_TEXT
        assert "const canDelete = item.can_delete;" in TEMPLATE_TEXT

    def test_render_thumbs_reciben_can_delete(self):
        """_renderPdfThumb/_renderExcelThumb reciben canDelete (per-file)."""
        assert "return _renderPdfThumb(errorId, filename, canDelete, scope);" in TEMPLATE_TEXT
        assert "return _renderExcelThumb(errorId, filename, canDelete, scope);" in TEMPLATE_TEXT

    def test_modal_delete_por_can_delete(self):
        """El botón delete del modal usa canDelete (no window._canWrite)."""
        assert "${canDelete ? `<button class=\"modal-delete-img\"" in TEMPLATE_TEXT


class TestPasteHandler:
    """FA-4: el paste handler usa _canFacturadorAttach para scope facturador."""

    def test_paste_allowed_facturador(self):
        """Paste a facturador se autoriza con _canFacturadorAttach (incluye :write)."""
        assert (
            "? window._canFacturadorAttach\n      : window._canWrite"
        ) in TEMPLATE_TEXT or (
            "window._canFacturadorAttach\n      : window._canWrite"
        ) in TEMPLATE_TEXT
