"""Migra las categorías heredadas de control-novedades a las dos vigentes.

"Factura Abierta" pasa a "Notificación"; "Otros", "Soportes de Carpeta",
"Carpeta no entregada", "Factura", "FURIPS" (y cualquier otro valor) pasan a
"Error". Solo cambia ``tipo_error``: no toca fechas ni ningún otro campo.

Uso (desde la raíz del proyecto, con el servicio DETENIDO):

    python -m scripts.migrar_categorias_novedades            # simulación
    python -m scripts.migrar_categorias_novedades --aplicar  # escribe

Sin ``--aplicar`` solo muestra los conteos. Con ``--aplicar`` primero copia el
JSON a ``control_errores.json.bak-AAAAMMDD-HHMMSS`` en la misma carpeta y luego
escribe con el mismo lock y la misma escritura atómica del almacén. Es
idempotente: una segunda corrida no cambia nada.
"""

import argparse
import json
import logging
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from app.utils import errores_storage
from app.utils.errores_storage import normalizar_tipo_error

logger = logging.getLogger(__name__)


def _leer_estricto() -> dict[str, Any]:
    """Lee el JSON de novedades fallando si no existe o no es válido.

    A diferencia de ``errores_storage._leer_datos`` no devuelve un almacén
    vacío ante un error: una migración nunca debe escribir sobre una lectura
    fallida.
    """
    data = json.loads(errores_storage.ERRORES_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("errores"), list):
        raise ValueError("Formato inesperado: falta la lista 'errores'")
    return data


def _conteo(errores: list[dict[str, Any]]) -> Counter:
    """Cuenta registros por ``tipo_error``."""
    return Counter(error.get("tipo_error") for error in errores)


def _respaldar() -> Path:
    """Copia el JSON actual junto al original y devuelve la ruta de la copia."""
    origen = errores_storage.ERRORES_FILE
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = origen.with_name(f"{origen.name}.bak-{marca}")
    shutil.copy2(origen, destino)
    return destino


def migrar(aplicar: bool = False) -> dict[str, Any]:
    """Mapea ``tipo_error`` de todos los registros a las categorías vigentes.

    Returns:
        ``{"total", "antes", "despues", "cambiados", "respaldo"}``; ``respaldo``
        es None en simulación o cuando no hay nada que cambiar.
    """
    with errores_storage._write_lock:
        data = _leer_estricto()
        errores = data["errores"]
        antes = _conteo(errores)
        cambiados = 0
        for error in errores:
            nuevo = normalizar_tipo_error(error.get("tipo_error"))
            if error.get("tipo_error") != nuevo:
                error["tipo_error"] = nuevo
                cambiados += 1
        despues = _conteo(errores)

        respaldo = None
        if aplicar and cambiados:
            respaldo = _respaldar()
            errores_storage._escribir_datos(data)
            if len(_leer_estricto()["errores"]) != len(errores):
                raise RuntimeError("La cantidad de registros cambió al escribir")
            logger.info("[BACK] Categorías migradas: %d registros", cambiados)

    return {
        "total": len(errores),
        "antes": dict(antes),
        "despues": dict(despues),
        "cambiados": cambiados,
        "respaldo": str(respaldo) if respaldo else None,
    }


def _imprimir(resultado: dict[str, Any], aplicar: bool) -> None:
    """Muestra los conteos antes y después."""
    print(f"Archivo: {errores_storage.ERRORES_FILE}")
    print(f"Registros: {resultado['total']}")
    print("Antes:")
    for tipo, cantidad in sorted(resultado["antes"].items(), key=lambda x: str(x[0])):
        print(f"  {tipo!s:<24} {cantidad:>6}  ->  {normalizar_tipo_error(tipo)}")
    print("Después:")
    for tipo, cantidad in sorted(resultado["despues"].items(), key=lambda x: str(x[0])):
        print(f"  {tipo!s:<24} {cantidad:>6}")
    print(f"Registros a cambiar: {resultado['cambiados']}")
    if not aplicar:
        print("SIMULACIÓN: no se escribió nada. Use --aplicar para escribir.")
    elif resultado["respaldo"]:
        print(f"Respaldo: {resultado['respaldo']}")
        print("Migración aplicada.")
    else:
        print("Nada que cambiar: el archivo ya estaba migrado.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Escribe los cambios (sin esto solo simula)",
    )
    args = parser.parse_args()
    _imprimir(migrar(aplicar=args.aplicar), args.aplicar)


if __name__ == "__main__":
    main()
