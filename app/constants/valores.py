"""Contrato de valores validos por campo (produccion del facturador).

Mapea campo interno (clave de indices / invoice.*) -> catalogos cuyos
valores, en UNION, son todos los valores reconocidos para ese campo.
Solo entran campos con semantica de allowlist: si un valor del Excel
no esta en ninguno de sus catalogos, el motor probablemente lo juzgue
mal (rama que no matchea o catch-all que dispara de mas).

NO entran catalogos con semantica de trigger/excepcion
(ej. codigos_tipo_procedimiento_laboratorio, codigos_exceptuados):
esos listan valores que disparan reglas, no todos los validos, y
usarlos aqui generaria falsos avisos en cada corrida.

La comparacion espeja al evaluador `in` del motor: NFC + strip +
upper (insensible a mayusculas, sensible a tildes). Un valor que solo
difiera en mayusculas matchea en el motor y no se reporta; uno con
tilde cambiada no matchea y si se reporta.
"""

from __future__ import annotations

#: Campo interno -> catalogos (keys de `catalogos`) en union.
FIELD_VALUE_CATALOGS: dict[str, tuple[str, ...]] = {
    "centro_costo": (
        "val_centros_costo_ambulatoria_validos",
        "centros_costo_laboratorio_validos",
        "centros_costo_pyp_intramural",
        "centros_costo_validos_urgencias",
        "centros_costo_validos_intramural",
        "centro_costo_pyp",
        "centro_costo_quirofano",
        "centro_costo_hospitalizacion",
    ),
    "tipo_usuario": (
        "tipo_usuario_validos",
    ),
}

#: Tope de valores desconocidos reportados por campo (anti-ruido).
MAX_UNKNOWN_VALUES_PER_FIELD = 20
