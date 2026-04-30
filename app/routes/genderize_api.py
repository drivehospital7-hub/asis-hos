"""Ruta para probar Genderize API."""

import logging

from flask import Blueprint, jsonify

from app.services.genderize_service import predict_genders

logger = logging.getLogger(__name__)

genderize_bp = Blueprint("genderize", __name__, url_prefix="/api/genderize")


# Lista de nombres de prueba (10 máximo por request de batch)
TEST_NAMES = [
    "Jhonar",
    "Erick",
    "Hijo de Sandra",
    "Yorladi",
    "Adriano",
    "Jhon",
    "Hijo de Yorlady",
    "Ivan",
    "Cristian",
    "Alba",
]


@genderize_bp.get("/")
def genderize_check():
    """Consulta genderize para la lista de nombres de prueba."""
    try:
        results, rate_limit = predict_genders(TEST_NAMES)

        data = {
            name: {
                "gender": r.gender,
                "probability": r.probability,
                "count": r.count,
            }
            for r, name in zip(results, TEST_NAMES)
        }

        # Agregar info de rate limit si está disponible
        response_data = {"status": "success", "data": data, "errors": []}
        if rate_limit:
            response_data["rate_limit"] = {
                "limit": rate_limit.limit,
                "remaining": rate_limit.remaining,
                "reset_seconds": rate_limit.reset,
            }

        return jsonify(response_data)
    except Exception as e:
        logger.exception("Error consultando genderize")
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 500