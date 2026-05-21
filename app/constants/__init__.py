"""Constantes compartidas del proyecto Control System.

Re-exporta todo desde los módulos por dominio para backward compatibility.
Este package reemplazará a app/constants.py en Fase 7 (cleanup).
"""

from __future__ import annotations

from app.constants.base import *            # noqa: F401, F403
from app.constants.columnas import *         # noqa: F401, F403
from app.constants.colores import *          # noqa: F401, F403
from app.constants.odontologia import *      # noqa: F401, F403
from app.constants.urgencias import *        # noqa: F401, F403
