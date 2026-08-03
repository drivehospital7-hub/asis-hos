"""Tests for observation-cell inline-edit write-back in control_errores.html.

Strict TDD — tests written before the template fix (RED).

Layer note: these are static source-assertion tests. No DOM harness is
available for this Jinja template: the frontend vitest suite runs in a
node-only environment (no jsdom; see frontend/vite.config.ts) and the
template is rendered server-side by Flask. The existing
test_visual_redesign.py already tests this template via read_text + assert,
so this file follows the same pattern.

We assert STRUCTURE and CONTRACT (the shared write-back helper exists, both
save paths delegate to it, the destructive bare write-back is gone, and the
non-regression guards hold), not visual style.
"""

from __future__ import annotations

from pathlib import Path


TEMPLATE = Path("app/templates/control_errores.html")


def _template_content() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


class TestObservationCellWriteBack:
    """Fix: the eye (image) button disappears when saving an observation edit."""

    def test_write_back_helper_is_defined(self):
        """The field-aware helper must be declared in the template script."""
        content = _template_content()
        assert "function updateObservationCellText(td, newText)" in content

    def test_both_save_paths_delegate_to_helper(self):
        """saveFromEditor and saveFromEditorWithCallback share the helper.

        Exactly two call sites — one per save function's trailing else.
        """
        content = _template_content()
        assert content.count("updateObservationCellText(currentCell, newValue)") == 2

    def test_bare_text_content_write_back_removed(self):
        """The destructive `currentCell.textContent = newValue || '-'` is gone."""
        content = _template_content()
        assert "currentCell.textContent = newValue || '-';" not in content

    def test_helper_targets_obs_cell_wrapper_for_observacion(self):
        """observacion branch: write into .obs-cell-wrapper, not the td."""
        content = _template_content()
        assert "td.dataset.field === 'observacion'" in content
        assert "td.querySelector('.obs-cell-wrapper')" in content

    def test_helper_targets_span_for_factura(self):
        """factura branch: write into the first span child, not the td."""
        content = _template_content()
        assert "td.dataset.field === 'factura'" in content
        assert "const span = td.querySelector('span');" in content

    def test_helper_falls_back_to_text_content(self):
        """Legacy rows without a wrapper fall back to td.textContent."""
        content = _template_content()
        assert "td.textContent = text;" in content
        assert "const text = newText || '-';" in content

    def test_helper_declared_before_save_functions(self):
        """Helper is declared before saveFromEditor (design placement)."""
        content = _template_content()
        helper_pos = content.index("function updateObservationCellText")
        save_from_editor_pos = content.index("async function saveFromEditor")
        assert helper_pos < save_from_editor_pos

    def test_open_editor_read_path_selector_contract_intact(self):
        """openEditor must still read from .obs-cell-wrapper (shared selector).

        Non-regression: the read path inside openEditor queries
        '.obs-cell-wrapper' — the fix must not rename or remove it.
        """
        content = _template_content()
        start = content.index("function openEditor(")
        end = content.index("function closeEditor(")
        open_editor_body = content[start:end]
        assert "td.querySelector('.obs-cell-wrapper')" in open_editor_body

    def test_estado_badge_branches_unchanged(self):
        """Non-regression: both save-path estado badge branches stay untouched.

        (openEditor's read-path `else if (field === 'estado')` at L742 is a
        different branch and must not be counted here.)
        """
        content = _template_content()
        badge_write = (
            'currentCell.innerHTML = `<span class="badge '
            "${newValue==='S'?'badge--pending':'badge--resolved'}\">"
            '${escapeHtml(newValue)}</span>`;'
        )
        assert content.count(badge_write) == 2

    def test_duplicate_reject_reverts_keep_bare_text_content(self):
        """Non-regression: duplicate-reject reverts stay on bare textContent.

        Out of scope for the helper (factura spans carry no interactive
        children), so both must remain exactly as-is.
        """
        content = _template_content()
        assert content.count("currentCell.textContent = errActual.factura || '-'") == 2
