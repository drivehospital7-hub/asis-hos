"""Blueprint for PDF term search."""

import json
import logging
import os
import re
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from app.constants import busqueda_pdf as busqueda_pdf_consts
from app.services.busqueda_pdf.sinonimos_storage import cargar_sinonimos, guardar_sinonimos
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

busqueda_pdf_bp = Blueprint("busqueda_pdf", __name__)

# Matches Windows drive absolute like C:\ or D:/ or C:/
_WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def _strip_outer_quotes(ruta: str) -> str:
    """Strip surrounding whitespace and outer quote characters.

    Handles user paste with literal quotes: '"D:\\path"' or "'D:\\path'".
    Iteratively strips because frontend/user may add multiple layers.
    """
    s = ruta.strip()
    # Remove outer matching quotes iteratively (e.g. ""D:\path"" or '"D:\path"')
    # Also handles mixed quotes via chained strip as fallback.
    # First, iterative matched-pair stripping
    while len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1].strip()
    # Fallback: strip any remaining leading/trailing quote chars (unbalanced paste)
    s = s.strip('"').strip("'").strip('"').strip("'").strip()
    return s


def _es_ruta_absoluta_windows(ruta: str) -> bool:
    """Return True for Windows absolute paths regardless of OS.

    Covers drive-letter (C:\\, D:/) and UNC (\\\\server\\share, //server/share).
    Used to avoid Linux isabs false-negative for Windows paths in dev/test.
    """
    if _WINDOWS_DRIVE_RE.match(ruta):
        return True
    if ruta.startswith("\\\\") or ruta.startswith("//"):
        return True
    return False


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


def _get_pdf_bases() -> list[str]:
    """Return configured PDF base paths, supporting monkeypatched constants in tests.

    Priority: PDF_BASE_PATHS list > legacy PDF_BASE_PATH fallback.
    Handles both env-driven and monkeypatched values.
    Returns empty list in open mode (no restriction).
    """
    bases: list[str] = []
    raw_bases = getattr(busqueda_pdf_consts, "PDF_BASE_PATHS", None)
    if isinstance(raw_bases, list) and raw_bases:
        bases = [str(b).strip() for b in raw_bases if str(b).strip()]

    legacy = getattr(busqueda_pdf_consts, "PDF_BASE_PATH", None)
    if isinstance(legacy, str) and legacy.strip():
        legacy_norm = legacy.strip()
        lower_bases = [b.lower() for b in bases]
        if legacy_norm.lower() not in lower_bases:
            bases.append(legacy_norm)

    return bases


def _is_within_base(ruta: str, base: str) -> bool:
    """Check if ruta is inside base (case-insensitive, UNC-aware).

    Tries Path.resolve().is_relative_to() first; falls back to
    normalized string prefix check with separator boundary.
    """
    # Attempt Path-based check (handles normalized drive/UNC when accessible)
    try:
        ruta_p = Path(ruta).resolve()
        base_p = Path(base).resolve()
        try:
            # Python 3.9+
            if ruta_p.is_relative_to(base_p):
                return True
        except AttributeError:
            # Fallback for older Python via string comparison on resolved
            rp_l = str(ruta_p).lower()
            bp_l = str(base_p).lower()
            if rp_l == bp_l:
                return True
            bp_prefix = bp_l.rstrip(os.sep)
            if rp_l.startswith(bp_prefix + os.sep):
                return True
        else:
            # is_relative_to returned False -> fall through to string check
            # (resolve may produce different drive casing, so still try string)
            pass
    except Exception:
        # Resolve may fail for unreachable UNC shares - fall back below
        pass

    # String fallback: case-insensitive, separator-aware
    ruta_norm = os.path.normpath(ruta.replace("/", os.sep)).lower()
    base_norm = os.path.normpath(base.replace("/", os.sep)).lower()
    if ruta_norm == base_norm:
        return True
    base_prefix = base_norm.rstrip(os.sep)
    return ruta_norm.startswith(base_prefix + os.sep)


def _collect_dir_diagnostics(ruta_normalizada: str) -> dict:
    """Collect exists/scandir/listdir signals for debug payload without side effects."""
    exists = None
    path_exists = None
    path_is_dir = None
    is_file = None
    scandir_err: str | None = None
    scandir_ok = False
    listdir_err: str | None = None
    listdir_ok = False

    try:
        exists = os.path.exists(ruta_normalizada)
    except Exception as exc:
        exists = f"exc:{type(exc).__name__}:{exc}"

    try:
        p = Path(ruta_normalizada)
        path_exists = p.exists()
        path_is_dir = p.is_dir()
    except Exception as exc:
        path_exists = f"exc:{type(exc).__name__}:{exc}"
        path_is_dir = f"exc:{type(exc).__name__}:{exc}"

    try:
        is_file = os.path.isfile(ruta_normalizada)
    except Exception as exc:
        is_file = f"exc:{type(exc).__name__}:{exc}"

    try:
        with os.scandir(ruta_normalizada) as it:
            next(iter(it), None)
        scandir_ok = True
    except FileNotFoundError as exc:
        scandir_err = f"FileNotFoundError: {exc}"
    except NotADirectoryError as exc:
        scandir_err = f"NotADirectoryError: {exc}"
    except OSError as exc:
        scandir_err = f"OSError({exc.errno}): {exc}"
    except Exception as exc:
        scandir_err = f"{type(exc).__name__}: {exc}"

    if not scandir_ok:
        # Always try listdir as final probe, even when exists flags are False
        try:
            os.listdir(ruta_normalizada)
            listdir_ok = True
        except OSError as exc:
            listdir_err = f"OSError({exc.errno}): {exc}"
        except Exception as exc:
            listdir_err = f"{type(exc).__name__}: {exc}"

    return {
        "ruta_normalizada": ruta_normalizada,
        "exists": exists,
        "path_exists": path_exists,
        "path_is_dir": path_is_dir,
        "is_file": is_file,
        "scandir_ok": scandir_ok,
        "scandir_err": scandir_err,
        "listdir_ok": listdir_ok,
        "listdir_err": listdir_err,
    }


def _try_probe_alternative_paths(ruta_normalizada: str) -> tuple[bool, str | None, str]:
    """Try alternative path forms when primary probe is ambiguous.

    Covers:
    - Forward-slash variant (monitoreo uses Path(rp.replace("\\", "/")))
    - Long UNC prefix \\?\\UNC\\ for Windows long paths / spaces
    - Path.resolve() variant
    Returns (is_valid, matched_path, reason_code).
    """
    candidates: list[str] = []

    # Forward-slash variant (useful on POSIX and for comparison with monitoreo)
    alt_slash = ruta_normalizada.replace("\\", "/")
    if alt_slash != ruta_normalizada:
        candidates.append(alt_slash)

    # Backslash variant if original used slashes
    alt_backslash = ruta_normalizada.replace("/", "\\")
    if alt_backslash != ruta_normalizada and alt_backslash not in candidates:
        candidates.append(alt_backslash)

    # Windows long UNC prefix \\?\UNC\server\share\...
    if os.name == "nt" and ruta_normalizada.startswith("\\\\") and not ruta_normalizada.startswith("\\\\?\\"):
        # Strip leading \\ and prefix with \\?\UNC\
        long_unc = "\\\\?\\UNC\\" + ruta_normalizada.lstrip("\\")
        if long_unc not in candidates:
            candidates.append(long_unc)
        # Also try long UNC with forward slashes normalized
        long_unc_fwd = long_unc.replace("/", "\\")
        if long_unc_fwd not in candidates:
            candidates.append(long_unc_fwd)

    # Path.resolve() string if different
    try:
        resolved = str(Path(ruta_normalizada).resolve())
        if resolved != ruta_normalizada and resolved not in candidates:
            candidates.append(resolved)
    except Exception:
        pass

    for cand in candidates:
        logger.debug("Trying alternative directory probe: %r (origin %r)", cand, ruta_normalizada)
        try:
            if os.path.isdir(cand):
                logger.info("Alternative path isdir ok: %r -> %r", ruta_normalizada, cand)
                return True, cand, "ok_alt_isdir"
        except Exception as exc:
            logger.debug("Alternative isdir exception for %r: %s", cand, exc)
        try:
            with os.scandir(cand) as it:
                next(iter(it), None)
            logger.warning(
                "isdir failed but alternative scandir ok: %r -> %r",
                ruta_normalizada, cand,
            )
            return True, cand, "ok_alt_scandir"
        except Exception:
            pass
        try:
            os.listdir(cand)
            logger.warning(
                "isdir/scandir failed but alternative listdir ok: %r -> %r",
                ruta_normalizada, cand,
            )
            return True, cand, "ok_alt_listdir"
        except Exception:
            pass

    return False, None, ""


def _diagnosticar_fallo_directorio(ruta_normalizada: str, ruta_original: str) -> tuple[bool, str | None, str]:
    """Try resilient checks to decide if ruta is a readable directory.

    Mirrors monitoreo's tolerant approach: os.path.isdir may be flaky for UNC
    (transient SMB, permission caching, race). Try os.path.exists,
    Path.exists, and os.scandir before giving up. Also tries unconditional
    os.listdir and alternative path forms (forward-slash, long UNC).

    Returns:
        (is_valid, parent_fallback, reason_code)
        is_valid True if directory is usable.
        parent_fallback is parent dir if ruta is a file whose parent is dir.
        reason_code: short code for error differentiation.
    """
    logger.debug(
        "Diagnosing directory: normalized=%r original=%r",
        ruta_normalizada, ruta_original,
    )

    # Fast path: isdir already checked by caller, but re-check with exception safety
    try:
        if os.path.isdir(ruta_normalizada):
            logger.debug("Directory probe ok_isdir: %r", ruta_normalizada)
            return True, None, "ok_isdir"
    except Exception as exc:
        logger.warning("os.path.isdir exception for %s: %s", ruta_normalizada, exc)

    # Gather diagnostics (always collected for logging)
    exists = False
    path_exists = False
    path_is_dir = False
    is_file = False
    exists_raw: object = False
    path_exists_raw: object = False
    try:
        exists = os.path.exists(ruta_normalizada)
        exists_raw = exists
    except Exception as exc:
        logger.warning("os.path.exists exception for %s: %s", ruta_normalizada, exc)
        exists_raw = f"exc:{exc}"
    try:
        p = Path(ruta_normalizada)
        path_exists = p.exists()
        path_is_dir = p.is_dir()
        path_exists_raw = path_exists
    except Exception as exc:
        logger.warning("Path.exists/is_dir exception for %s: %s", ruta_normalizada, exc)
        path_exists_raw = f"exc:{exc}"
    try:
        is_file = os.path.isfile(ruta_normalizada)
    except Exception:
        pass

    logger.debug(
        "Probe prelim: normalized=%r exists=%r path_exists=%r path_is_dir=%r is_file=%r",
        ruta_normalizada, exists_raw, path_exists_raw, path_is_dir, is_file,
    )

    # Case: ruta is a file (e.g. user pasted PDF path). Allow parent dir if navigable.
    if is_file or (path_exists and not path_is_dir and exists):
        parent = os.path.dirname(ruta_normalizada)
        if parent and parent != ruta_normalizada:
            try:
                if os.path.isdir(parent):
                    logger.info("Ruta es archivo, usando carpeta padre: %s -> %s", ruta_normalizada, parent)
                    return True, parent, "archivo_parent"
            except Exception:
                pass
            # Also try scandir on parent as resilience
            try:
                with os.scandir(parent) as it:
                    next(iter(it), None)
                logger.info("Ruta es archivo, parent scandir ok: %s -> %s", ruta_normalizada, parent)
                return True, parent, "archivo_parent_scandir"
            except Exception:
                pass
        logger.warning(
            "Ruta no es directorio (es archivo): %s exists=%s isdir=False path_exists=%s path_is_dir=%s",
            ruta_normalizada, exists, path_exists, path_is_dir,
        )
        return False, None, "es_archivo"

    # Try scandir as resilient directory probe (works for UNC when isdir is flaky)
    scandir_ok = False
    scandir_err: str | None = None
    try:
        with os.scandir(ruta_normalizada) as it:
            next(iter(it), None)
        scandir_ok = True
    except FileNotFoundError as exc:
        scandir_err = f"FileNotFoundError: {exc}"
    except NotADirectoryError as exc:
        scandir_err = f"NotADirectoryError: {exc}"
    except OSError as exc:
        scandir_err = f"OSError({exc.errno}): {exc}"
    except Exception as exc:
        scandir_err = f"{type(exc).__name__}: {exc}"

    if scandir_ok:
        logger.warning(
            "isdir failed but scandir ok for %s: exists=%s path_exists=%s path_is_dir=%s -> considering valid",
            ruta_normalizada, exists, path_exists, path_is_dir,
        )
        return True, None, "ok_scandir"

    # Fallback: if any existence flag true, try listdir (legacy path)
    if exists or path_exists:
        try:
            os.listdir(ruta_normalizada)
            logger.warning(
                "isdir failed but listdir ok for %s: exists=%s path_exists=%s -> considering valid",
                ruta_normalizada, exists, path_exists,
            )
            return True, None, "ok_listdir"
        except OSError as exc:
            prev = scandir_err or ""
            scandir_err = f"listdir OSError: {exc} (prev={prev})"
        except Exception as exc:
            prev = scandir_err or ""
            scandir_err = f"listdir {type(exc).__name__}: {exc} (prev={prev})"

    # Critical: unconditional listdir probe even when exists flags are False.
    # On some UNC setups exists/isdir are False due to permission caching,
    # but listdir still succeeds when re-authenticating.
    try:
        os.listdir(ruta_normalizada)
        logger.warning(
            "isdir/exists false but unconditional listdir ok for %s -> considering valid (scandir_err=%s)",
            ruta_normalizada, scandir_err,
        )
        return True, None, "ok_listdir_unconditional"
    except FileNotFoundError as exc:
        # Keep most informative error
        if not scandir_err or "FileNotFoundError" not in scandir_err:
            scandir_err = f"listdir FileNotFoundError: {exc} (prev={scandir_err})"
    except NotADirectoryError as exc:
        if not scandir_err or "NotADirectoryError" not in scandir_err:
            scandir_err = f"listdir NotADirectoryError: {exc} (prev={scandir_err})"
    except OSError as exc:
        if scandir_err is None:
            scandir_err = f"listdir OSError({exc.errno}): {exc}"
        else:
            scandir_err = f"{scandir_err} | listdir OSError({exc.errno}): {exc}"
    except Exception as exc:
        if scandir_err is None:
            scandir_err = f"listdir {type(exc).__name__}: {exc}"
        else:
            scandir_err = f"{scandir_err} | listdir {type(exc).__name__}: {exc}"

    # Try alternative path forms (forward-slash, long UNC, resolved)
    alt_valid, alt_path, alt_reason = _try_probe_alternative_paths(ruta_normalizada)
    if alt_valid:
        # If alternative matched, consider original valid (same share, different syntax)
        # Return alt_path as fallback only if it is meaningfully different and original probe failed
        # For directory equivalence we return original normalized as valid
        logger.info("Alternative probe succeeded for %r via %r reason=%s", ruta_normalizada, alt_path, alt_reason)
        return True, None, alt_reason

    logger.warning(
        "Ruta no encontrada or not directory: %s exists=%s isdir=False path_exists=%s path_is_dir=%s scandir_err=%s",
        ruta_normalizada, exists, path_exists, path_is_dir, scandir_err,
    )
    logger.debug(
        "Full diagnostics for %r: exists=%r path_exists=%r path_is_dir=%r scandir_err=%r",
        ruta_normalizada, exists_raw, path_exists_raw, path_is_dir, scandir_err,
    )
    return False, None, "no_encontrada"


def _validar_ruta_con_detalle(ruta: str) -> tuple[str | None, str | None]:
    """Validate ruta and return (normalized_path, reason_code).

    reason_code is None when valid, otherwise one of:
      vacia, traversal, relativa, fuera_base, es_archivo, no_encontrada, ok_*
    """
    if not ruta or not ruta.strip():
        logger.debug("Ruta validation failed: vacia raw=%r", ruta)
        return None, "vacia"

    # Strip outer quotes and whitespace (frontend or user may paste "D:\path" with quotes)
    raw = _strip_outer_quotes(ruta)
    if not raw:
        logger.debug("Ruta validation failed: vacia after quote strip raw=%r orig=%r", raw, ruta)
        return None, "vacia"

    # Block path traversal: check Path parts for ".." (not substring)
    # Note: "9. SOAT" contains dot+space but not "..", so it must NOT trigger.
    try:
        if ".." in Path(raw).parts:
            logger.debug("Ruta traversal blocked: raw=%r parts=%r", raw, Path(raw).parts)
            return None, "traversal"
        # Also check forward-slash split for cross-OS (e.g. POSIX handling of Windows paths)
        if ".." in raw.replace("\\", "/").split("/"):
            logger.debug("Ruta traversal blocked (slash split): raw=%r", raw)
            return None, "traversal"
    except Exception:
        if ".." in raw.split("\\") or ".." in raw.split("/"):
            logger.debug("Ruta traversal blocked (fallback split): raw=%r", raw)
            return None, "traversal"

    # Normalize preserving UNC leading \\ via normpath.
    # os.path.normpath on Windows preserves leading \\ for UNC.
    # Also handle forward-slash UNC (//server/share) -> normpath converts to \\server\share.
    # Detect UNC and Windows drive early so is_absolute check is OS-agnostic
    # (Linux POSIX would treat \\ and D:\ as relative).
    is_unc = raw.startswith("\\\\") or raw.startswith("//")
    is_windows_abs = _es_ruta_absoluta_windows(raw)
    # Use same forward-slash conversion as monitoreo for cross-platform resilience,
    # but keep OS native normpath for filesystem calls on Windows.
    if (is_unc or is_windows_abs) and os.name != "nt":
        # On POSIX, convert \\ to / and preserve leading // for UNC, and D:/ for drive
        tmp = raw.replace("\\", "/")
        ruta_normalizada = os.path.normpath(tmp)
        # posixpath.normpath preserves leading // per POSIX spec, but ensure it
        if tmp.startswith("//") and not ruta_normalizada.startswith("//"):
            # Restore UNC double slash if collapsed to single
            ruta_normalizada = "/" + ruta_normalizada if ruta_normalizada.startswith("/") else "//" + ruta_normalizada.lstrip("/")
    else:
        ruta_normalizada = os.path.normpath(raw.replace("/", os.sep))

    # Detailed debug log that ALWAYS fires (before any early return)
    try:
        isabs_os = os.path.isabs(ruta_normalizada)
    except Exception as exc:
        isabs_os = f"exc:{exc}"
    try:
        isabs_path = Path(ruta_normalizada).is_absolute()
    except Exception as exc:
        isabs_path = f"exc:{exc}"
    bases = _get_pdf_bases()
    logger.debug(
        "Validating ruta: raw=%r normalized=%r is_unc=%s is_windows_abs=%s isabs_os=%r isabs_path=%r bases=%r",
        raw, ruta_normalizada, is_unc, is_windows_abs, isabs_os, isabs_path, bases,
    )

    # Reject relative paths (UNC and Windows drive are always absolute, regardless of OS)
    is_absolute = False
    if is_unc or is_windows_abs:
        is_absolute = True
    else:
        if os.path.isabs(ruta_normalizada) or Path(ruta_normalizada).is_absolute():
            is_absolute = True
        else:
            # Extra check for forward-slash variant (covers Linux handling of Windows paths)
            alt = ruta_normalizada.replace("\\", "/")
            if alt != ruta_normalizada and (os.path.isabs(alt) or alt.startswith("/")):
                is_absolute = True
                # Keep normalized as alt for subsequent filesystem probes on POSIX
                if os.name != "nt":
                    ruta_normalizada = alt

    if not is_absolute:
        logger.debug(
            "Ruta rejected as relative: raw=%r normalized=%r is_unc=%s is_windows_abs=%s isabs_os=%r isabs_path=%r",
            raw, ruta_normalizada, is_unc, is_windows_abs, isabs_os, isabs_path,
        )
        return None, "relativa"

    # Base gate only when bases are explicitly configured (restricted mode)
    if bases:
        allowed = False
        for base in bases:
            if _is_within_base(ruta_normalizada, base):
                allowed = True
                break
        if not allowed:
            logger.info("Ruta blocked outside allowed bases: %s bases=%s", ruta, bases)
            return None, "fuera_base"

    # Resilient directory check (after base gate)
    is_valid, parent_fallback, reason = _diagnosticar_fallo_directorio(ruta_normalizada, ruta)
    logger.debug(
        "Directory diagnosis result: ruta=%r normalized=%r valid=%s reason=%s parent_fallback=%r",
        raw, ruta_normalizada, is_valid, reason, parent_fallback,
    )
    if is_valid:
        # If ruta was a file and parent is valid, return parent
        if parent_fallback:
            return parent_fallback, None
        return ruta_normalizada, None

    logger.debug("Ruta validation failed: raw=%r normalized=%r reason=%s", raw, ruta_normalizada, reason)
    return None, reason


def _validar_ruta(ruta: str) -> str | None:
    """Validate that ruta exists, has no traversal, and respects optional base gate.

    When PDF bases are configured (restricted mode), ruta must be inside at
    least one base (case-insensitive, separator-aware). When bases is empty
    (open mode), any absolute path is allowed.

    Returns:
        Normalized path if valid, None if invalid.
    """
    result, _ = _validar_ruta_con_detalle(ruta)
    return result


def _build_enriched_error(ruta: str, motivo: str | None) -> tuple[str, dict]:
    """Build enriched error message and debug payload for directory failures."""
    raw = _strip_outer_quotes(ruta) if ruta else ""
    try:
        # Normalize with Windows-aware handling for debug display
        if raw and _es_ruta_absoluta_windows(raw) and os.name != "nt":
            ruta_norm = os.path.normpath(raw.replace("\\", "/")) if raw else ""
        else:
            ruta_norm = os.path.normpath(raw.replace("/", os.sep)) if raw else ""
    except Exception:
        ruta_norm = raw

    diagnostics = _collect_dir_diagnostics(ruta_norm) if ruta_norm else {}

    # Base messages per reason
    if motivo == "fuera_base":
        base_msg = f"Ruta fuera de base permitida: {ruta}"
    elif motivo == "traversal":
        base_msg = "Ruta invalida: contiene '..'"
    elif motivo == "relativa":
        base_msg = "Ruta invalida: debe ser absoluta"
    elif motivo == "vacia":
        base_msg = "La ruta no puede estar vacia"
    elif motivo == "es_archivo":
        base_msg = f"La ruta no es un directorio: {ruta}"
    elif motivo == "no_encontrada":
        base_msg = f"Ruta no encontrada: {ruta}"
    else:
        base_msg = f"Ruta no encontrada: {ruta}"

    # Enrich with diagnostics for directory-related failures
    if motivo in ("no_encontrada", "es_archivo") and diagnostics:
        motivo_str = motivo or "unknown"
        scandir_err = diagnostics.get("scandir_err") or diagnostics.get("listdir_err") or "n/a"
        exists = diagnostics.get("exists")
        path_exists = diagnostics.get("path_exists")
        path_is_dir = diagnostics.get("path_is_dir")
        base_msg = (
            f"{base_msg} (motivo={motivo_str}, exists={exists}, "
            f"path_exists={path_exists}, path_is_dir={path_is_dir}, "
            f"scandir_err={scandir_err})"
        )

    # Debug payload for frontend (avoids needing server logs)
    debug_payload: dict = {}
    if diagnostics:
        # Keep only serializable primitives
        debug_payload = {
            "motivo": motivo,
            "ruta": ruta,
            "ruta_normalizada": diagnostics.get("ruta_normalizada"),
            "exists": str(diagnostics.get("exists")),
            "path_exists": str(diagnostics.get("path_exists")),
            "path_is_dir": str(diagnostics.get("path_is_dir")),
            "is_file": str(diagnostics.get("is_file")),
            "scandir_ok": diagnostics.get("scandir_ok"),
            "scandir_err": diagnostics.get("scandir_err"),
            "listdir_ok": diagnostics.get("listdir_ok"),
            "listdir_err": diagnostics.get("listdir_err"),
        }

    return base_msg, debug_payload


@busqueda_pdf_bp.get("/busqueda-pdf/")
@permiso_requerido("busqueda_pdf")
def react_shell():
    """React shell for PDF search."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/busqueda-pdf/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Busqueda PDF",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
            "pdf_base_path": busqueda_pdf_consts.PDF_BASE_PATH,
        },
    )


@busqueda_pdf_bp.get("/busqueda-pdf/listar-directorios")
@permiso_requerido("busqueda_pdf")
def listar_directorios():
    """List subdirectories and PDF files for a path."""
    ruta = request.args.get("ruta", "").strip()

    ruta_valida, motivo = _validar_ruta_con_detalle(ruta)
    if ruta_valida is None:
        msg, debug = _build_enriched_error(ruta, motivo)
        logger.debug("listar_directorios validation failed: ruta=%r motivo=%r debug=%r", ruta, motivo, debug)
        return jsonify({
            "status": "error",
            "data": {"debug": debug} if debug else {},
            "errors": [msg],
        }), 400

    try:
        entries = os.listdir(ruta_valida)
    except OSError as exc:
        logger.warning("Failed to list directory %r (validated %r): %s", ruta, ruta_valida, exc)
        # Provide diagnostics for listdir failure after validation passed
        diag = _collect_dir_diagnostics(ruta_valida)
        msg = f"No se pudo leer el directorio: {ruta} (scandir_err={diag.get('scandir_err') or diag.get('listdir_err')})"
        return jsonify({
            "status": "error",
            "data": {"debug": diag},
            "errors": [msg],
        }), 400

    directorios = []
    pdfs = []

    for entry in sorted(entries):
        entry_path = os.path.join(ruta_valida, entry)
        if os.path.isdir(entry_path):
            directorios.append({
                "nombre": entry,
                "ruta_completa": entry_path,
            })
        elif entry.lower().endswith(".pdf"):
            pdfs.append(entry)

    return jsonify({
        "status": "success",
        "data": {
            "directorios": directorios,
            "pdfs": pdfs,
        },
        "errors": [],
    })


@busqueda_pdf_bp.get("/busqueda-pdf/sinonimos")
@permiso_requerido("busqueda_pdf")
def get_sinonimos():
    """Return persisted synonyms."""
    sinonimos = cargar_sinonimos()
    return jsonify({
        "status": "success",
        "data": {"sinonimos": sinonimos},
        "errors": [],
    })


@busqueda_pdf_bp.post("/busqueda-pdf/sinonimos")
@permiso_requerido("busqueda_pdf")
def save_sinonimos():
    """Save synonyms sent from frontend."""
    data = request.get_json(silent=True)
    if not data or "sinonimos" not in data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Se requiere el campo 'sinonimos'"],
        }), 400

    sinonimos = data["sinonimos"]
    if not isinstance(sinonimos, dict):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["'sinonimos' debe ser un dict"],
        }), 400

    try:
        guardar_sinonimos(sinonimos)
        return jsonify({
            "status": "success",
            "data": {"sinonimos": sinonimos},
            "errors": [],
        })
    except OSError:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Error al guardar los sinonimos"],
        }), 500


@busqueda_pdf_bp.post("/busqueda-pdf/buscar")
@permiso_requerido("busqueda_pdf")
def buscar():
    """Search terms in PDFs inside a folder."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Cuerpo de request invalido"],
        }), 400

    ruta = data.get("ruta", "").strip()
    condicion = data.get("condicion", "").strip()
    transporte = data.get("transporte", "").strip()
    sinonimos = data.get("sinonimos")

    if not ruta:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta no puede estar vacia"],
        }), 400

    ruta_valida, motivo = _validar_ruta_con_detalle(ruta)
    if ruta_valida is None:
        msg, debug = _build_enriched_error(ruta, motivo)
        logger.debug("buscar validation failed: ruta=%r motivo=%r debug=%r", ruta, motivo, debug)
        return jsonify({
            "status": "error",
            "data": {"debug": debug} if debug else {},
            "errors": [msg],
        }), 400

    try:
        from app.services.busqueda_pdf.buscador import buscar_en_carpeta

        result = buscar_en_carpeta(ruta_valida, condicion, transporte, sinonimos)

        return jsonify({
            "status": "success",
            "data": result,
            "errors": [],
        })
    except Exception:
        logger.exception("Error en busqueda de PDFs")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Error interno al procesar la busqueda"],
        }), 500
