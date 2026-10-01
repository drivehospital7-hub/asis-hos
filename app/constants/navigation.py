"""Registro canonico de navegacion (sidebar unico).

Unica fuente de verdad para el sidebar Jinja (``base.html``) y el sidebar
React (via ``GET /api/nav``). Antes cada sidebar hardcodeaba su propia
lista y se desincronizaban en cada modulo nuevo.

Cada modulo::

    {"key": ..., "label": ..., "href": ..., "icon": ..., "endpoint": ...}

- ``key``: permiso base requerido. ``"*"`` = solo admin, ``None`` = visible
  para cualquier usuario autenticado (hoy solo ``/dashboard``).
- ``href``: URL que usa el sidebar React (coincide con sus hrefs actuales).
- ``icon``: nombre de icono lucide (conserva los valores de ``base.html``).
- ``endpoint``: endpoint Flask usado por ``url_for`` en la template Jinja.

Notas de verificacion:

- ``admin-reglas`` (``reglas_admin.reglas_admin_react``) esta protegido por
  ``@admin_requerido`` → key ``"*"``.
- ``auditoria`` (``derechos.auditoria_react``) esta protegido por
  ``@permiso_requerido("derechos")`` → key ``"derechos"`` (no existe un
  permiso ``"auditoria"`` como puerta de ruta; el permiso ``"auditoria"``
  de ``ALLOWED_PERMISOS`` solo se usa en ``DASHBOARD_AREAS``).
- ``traslado-facturas`` acepta ``traslado_facturas`` o ``monitoreo_carpetas``
  en ruta; el registro usa la key primaria ``"traslado_facturas"``.

``DASHBOARD_AREAS`` (``app/constants/base.py``) NO se toca: son las cards
del dashboard, otra superficie.
"""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


NAV_MODULES: list[dict] = [
    {
        "key": None,
        "label": "Panel principal",
        "href": "/dashboard",
        "icon": "LayoutDashboard",
        "endpoint": "home.home_react",
    },
    {
        "key": "procesar",
        "label": "Procesar",
        "href": "/procesar",
        "icon": "FileText",
        "endpoint": "procesar.procesar_react",
    },
    {
        "key": "control_urgencias",
        "label": "Control de Novedades",
        "href": "/control-novedades",
        "icon": "ClipboardCheck",
        "endpoint": "control_errores.control_errores_page",
    },
    {
        "key": "facturas_abiertas",
        "label": "Abiertas Urgencias",
        "href": "/abiertas-urgencias",
        "icon": "CalendarClock",
        "endpoint": "abiertas_urgencias.abiertas_urgencias_react",
    },
    {
        "key": "busqueda_pdf",
        "label": "Búsqueda PDF",
        "href": "/busqueda-pdf",
        "icon": "Search",
        "endpoint": "busqueda_pdf.react_shell",
    },
    {
        "key": "cronograma_urgencias",
        "label": "Cronograma Urgencias",
        "href": "/cronograma-urgencias",
        "icon": "CalendarClock",
        "endpoint": "cronograma_urgencias.cronograma_urgencias_react",
    },
    {
        "key": "cronograma_bacteriologas",
        "label": "Cronograma Bacteriólogas",
        "href": "/cronograma-bacteriologas",
        "icon": "CalendarClock",
        "endpoint": "cronograma_bacteriologas.cronograma_react",
    },
    {
        "key": "equipos_basicos",
        "label": "Ordenado y Facturado",
        "href": "/ordenado-facturado",
        "icon": "FileSpreadsheet",
        "endpoint": "ordenado_facturado.ordenado_facturado_react",
    },
    {
        "key": "derechos",
        "label": "Derechos",
        "href": "/derechos",
        "icon": "Scale",
        "endpoint": "derechos.derechos_react",
    },
    {
        "key": "derechos",
        "label": "Auditoría PDF",
        "href": "/derechos/auditoria",
        "icon": "FileSearch",
        "endpoint": "derechos.auditoria_react",
    },
    {
        "key": "monitoreo_carpetas",
        "label": "Monitoreo de Carpetas",
        "href": "/monitoreo-carpetas",
        "icon": "FolderSearch",
        "endpoint": "monitoreo_carpetas.index",
    },
    {
        "key": "traslado_facturas",
        "label": "Traslado de Facturas",
        "href": "/traslado-facturas",
        "icon": "ArrowRightLeft",
        "endpoint": "traslado_facturas.index",
    },
    {
        "key": "cruce_produccion",
        "label": "Cruce Producción",
        "href": "/cruce-produccion",
        "icon": "ArrowLeftRight",
        "endpoint": "cruce_produccion.index",
    },
    {
        "key": "examenes",
        "label": "Exámenes",
        "href": "/examenes",
        "icon": "FlaskConical",
        "endpoint": "examenes.examenes_react",
    },
    {
        "key": "*",
        "label": "Usuarios",
        "href": "/auth/usuarios",
        "icon": "Users",
        "endpoint": "auth.usuarios_react",
    },
    {
        "key": "*",
        "label": "Importar Facturas",
        "href": "/import-facturas",
        "icon": "upload",
        "endpoint": "import_facturas.import_facturas_react",
    },
    {
        "key": "*",
        "label": "Catálogos",
        "href": "/catalogo",
        "icon": "BookType",
        "endpoint": "catalogo.catalogo_react",
    },
    {
        "key": "*",
        "label": "Admin Reglas",
        "href": "/admin/reglas",
        "icon": "Settings",
        "endpoint": "reglas_admin.reglas_admin_react",
    },
]


def expandir(permisos: list[str] | tuple[str, ...] | set[str] | frozenset | None) -> set[str]:
    """Expande permisos ``X:write`` a su base ``X``.

    Unica implementacion de la regla (antes triplicada entre ``base.html``,
    el sidebar React y ``DASHBOARD_AREAS``). No duplicar en otros modulos.
    """
    expanded = set(permisos or [])
    for p in list(expanded):
        if isinstance(p, str) and p.endswith(":write"):
            expanded.add(p.removesuffix(":write"))
    return expanded


def modulos_para(
    permisos: list[str] | tuple[str, ...] | set[str] | frozenset | None,
    autenticado: bool,
) -> list[dict]:
    """Filtra ``NAV_MODULES`` segun permisos de sesion.

    - ``"*"`` en permisos → todos los modulos.
    - key ``None`` → solo si ``autenticado``.
    - otro key → solo si esta en los permisos expandidos.
    """
    perms = permisos or []
    if "*" in perms:
        return list(NAV_MODULES)
    expanded = expandir(perms)
    return [
        m
        for m in NAV_MODULES
        if (m["key"] is None and autenticado) or (m["key"] is not None and m["key"] in expanded)
    ]
