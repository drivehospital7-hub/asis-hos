"""Sinónimos para términos de búsqueda en PDFs."""

from app.constants.busqueda_pdf import SINONIMOS_DEFAULT


def merge_sinonimos(sinonimos_custom: dict | None) -> dict:
    """Combina SINONIMOS_DEFAULT + custom. Custom gana en colisión.

    Args:
        sinonimos_custom: Dict opcional con sinónimos customizados.

    Returns:
        Dict combinado de sinónimos.
    """
    result = dict(SINONIMOS_DEFAULT)

    if sinonimos_custom:
        result.update(sinonimos_custom)

    return result
