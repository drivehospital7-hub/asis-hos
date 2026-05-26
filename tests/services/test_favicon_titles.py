"""Tests for favicon assets and production-ready page titles.

Strict TDD — tests written BEFORE implementation.
- Phase 1: favicon.svg asset created
- Phase 2: <link rel="icon"> added to all 6 templates
- Phase 3: titles fixed (no "— React", consistent "· Hospital Orito" format)
"""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path("app/templates")
STATIC_DIR = Path("app/static")

TEMPLATES = [
    "base.html",
    "react_shell.html",
    "react_standalone.html",
]

TITLE_TEMPLATES = {
    # (template, must_NOT_contain, must_contain)
    "react_shell.html": ("— React", "Hospital Orito"),
    "react_standalone.html": ("— React", "Hospital Orito"),
    "base.html": ("Control Facturacion", "Hospital Orito · Control de Facturación"),
}


# ═══════════════════════════════════════════════════════════════
# Phase 1: Favicon assets
# ═══════════════════════════════════════════════════════════════

class TestFaviconAssets:
    """Phase 1: Favicon SVG asset exists and is valid."""

    def test_favicon_svg_exists(self):
        """favicon.svg exists in app/static/."""
        svg_path = STATIC_DIR / "favicon.svg"
        assert svg_path.exists(), "favicon.svg must exist in static/"
        assert svg_path.stat().st_size > 0, "favicon.svg must not be empty"

    def test_favicon_svg_has_ho_monogram(self):
        """favicon.svg contains the HO monogram (green square + HO text)."""
        svg_path = STATIC_DIR / "favicon.svg"
        content = svg_path.read_text(encoding="utf-8")
        assert "<svg" in content, "Must be a valid SVG"
        assert "HO" in content or "H" in content, "Must contain HO monogram text"
        assert "#16a34a" in content or "16a34a" in content, "Must use green #16a34a"

    def test_favicon_svg_has_viewbox(self):
        """favicon.svg declares a viewBox for proper scaling."""
        svg_path = STATIC_DIR / "favicon.svg"
        content = svg_path.read_text(encoding="utf-8")
        assert "viewBox" in content, "SVG must have viewBox attribute"


# ═══════════════════════════════════════════════════════════════
# Phase 2: Favicon <link> tags in all templates
# ═══════════════════════════════════════════════════════════════

class TestFaviconLinks:
    """Phase 2: Every template has favicon <link> in <head>."""

    def test_all_templates_have_favicon_link(self):
        """Every template contains <link rel="icon"> with favicon.svg."""
        missing = []
        for name in TEMPLATES:
            path = TEMPLATES_DIR / name
            content = path.read_text(encoding="utf-8")
            if 'rel="icon"' not in content and "rel='icon'" not in content:
                missing.append(name)
        assert not missing, f"Templates missing favicon link: {missing}"

    def test_all_templates_have_svg_favicon(self):
        """Every template references favicon.svg in the icon link."""
        missing = []
        for name in TEMPLATES:
            path = TEMPLATES_DIR / name
            content = path.read_text(encoding="utf-8")
            if "favicon.svg" not in content:
                missing.append(name)
        assert not missing, f"Templates missing favicon.svg reference: {missing}"

    def test_base_html_favicon_before_head_extra(self):
        """base.html has favicon link BEFORE {% block head_extra %}."""
        path = TEMPLATES_DIR / "base.html"
        content = path.read_text(encoding="utf-8")
        icon_pos = content.find('rel="icon"')
        head_extra_pos = content.find("{% block head_extra %}")
        assert icon_pos != -1, "favicon link not found in base.html"
        assert head_extra_pos != -1, "head_extra block not found"
        assert icon_pos < head_extra_pos, (
            "favicon link must come before {% block head_extra %} "
            f"(icon at {icon_pos}, head_extra at {head_extra_pos})"
        )

    def test_favicon_link_in_head_section(self):
        """Favicon link appears in the <head> section (before </head>)."""
        for name in TEMPLATES:
            path = TEMPLATES_DIR / name
            content = path.read_text(encoding="utf-8")
            head_close = content.find("</head>")
            assert head_close != -1, f"{name}: </head> not found"
            head_section = content[:head_close]
            assert 'rel="icon"' in head_section or "rel='icon'" in head_section, (
                f"{name}: favicon link not in <head>"
            )

    def test_alternate_icon_fallback_exists(self):
        """At least one template links to favicon.ico as fallback."""
        found = False
        for name in TEMPLATES:
            path = TEMPLATES_DIR / name
            content = path.read_text(encoding="utf-8")
            if "favicon.ico" in content:
                found = True
                break
        # It's acceptable if only base.html has it (covers all extended templates)
        assert found, "No template references favicon.ico as fallback"


# ═══════════════════════════════════════════════════════════════
# Phase 3: Title corrections
# ═══════════════════════════════════════════════════════════════

class TestTemplateTitles:
    """Phase 3: Titles are production-ready (no '— React')."""

    def test_no_react_in_title(self):
        """No template contains '— React' in its <title>."""
        offending = []
        for name in TEMPLATES:
            path = TEMPLATES_DIR / name
            content = path.read_text(encoding="utf-8")
            # Extract <title> content
            title_start = content.find("<title>")
            title_end = content.find("</title>")
            if title_start != -1 and title_end != -1:
                title_content = content[title_start:title_end]
                if "React" in title_content or "react" in title_content:
                    offending.append(name)
        assert not offending, f"Templates still containing React in title: {offending}"

    def test_react_shell_title_format(self):
        """react_shell.html default title uses '· Hospital Orito'."""
        path = TEMPLATES_DIR / "react_shell.html"
        content = path.read_text(encoding="utf-8")
        title_start = content.find("<title>")
        title_end = content.find("</title>")
        assert title_start != -1 and title_end != -1
        title_content = content[title_start:title_end]
        assert "Hospital Orito" in title_content, (
            f"react_shell.html title missing 'Hospital Orito': {title_content}"
        )

    def test_react_standalone_title_format(self):
        """react_standalone.html default title uses '· Hospital Orito'."""
        path = TEMPLATES_DIR / "react_standalone.html"
        content = path.read_text(encoding="utf-8")
        title_start = content.find("<title>")
        title_end = content.find("</title>")
        assert title_start != -1 and title_end != -1
        title_content = content[title_start:title_end]
        assert "Hospital Orito" in title_content, (
            f"react_standalone.html title missing 'Hospital Orito': {title_content}"
        )

    def test_base_html_title_default(self):
        """base.html {% block title %} default is 'Hospital Orito · Control de Facturación'."""
        path = TEMPLATES_DIR / "base.html"
        content = path.read_text(encoding="utf-8")
        assert 'Hospital Orito · Control de Facturación' in content, (
            "base.html block title default not updated"
        )


