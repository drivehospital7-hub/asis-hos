"""Servicio para consumir Genderize API con urllib."""
import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

logger = logging.getLogger(__name__)
GENDERIZE_API_URL = "https://api.genderize.io"


@dataclass
class GenderResult:
    """Resultado de genderize para un nombre."""

    name: str
    gender: str | None
    probability: float | None
    count: int | None


def predict_ genders( names: list[str]) -> list[GenderResult]:
    """Obtiene predicciones de género para una lista de nombres.

    Args:
        names: Lista de nombres (máximo 10).

    Returns:
        Lista de GenderResult con las predicciones.
    """
    if not names:
        return []

    params = [(f"name[{i}]", name) for i, name in enumerate(names)]
    query = urlencode(params)
    url = f"{GENDERIZE_API_URL}?{query}"

    logger.info("Consultando genderize para %d nombres", len(names))

    try:
        with urlopen(url, timeout=30) as response:
            data: list[dict[str, Any]] = json.load(response)
    except HTTPError as e:
        logger.exception("Error HTTP genderize: %s", e.code)
        raise

    results = [
        GenderResult(
            name=item.get("name", ""),
            gender=item.get("gender"),
            probability=item.get("probability"),
            count=item.get("count"),
        )
        for item in data
    ]

    logger.info("Recibidos %d resultados", len(results))
    return results