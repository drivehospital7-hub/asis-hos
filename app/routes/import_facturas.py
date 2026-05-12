"""Ruta para extraer nombres del Excel."""

import logging
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import genderize_extractor, genderize_service, genderize_verifier

logger = logging.getLogger(__name__)

import_facturas_bp = Blueprint("import_facturas", __name__)


@import_facturas_bp.route("/import-facturas")
def import_facturas_page():
    """Página para subir Excel y extraer nombres."""
    return render_template("import_facturas.html")


@import_facturas_bp.route("/api/import/facturas-nombres", methods=["POST"])
def extract_facturas_nombres():
    """Extrae Numero Factura - Primer Nombre - Sexo del Excel de facturas."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontró archivo Excel"]
        }), 400
    
    file = request.files["file"]
    
    # Guardar temporalmente
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name
    
    try:
        results = genderize_extractor.extract_factura_nombre_sexo(tmp_path)
        
        # Convertir a dict para JSON
        data = [
            {
                "numero_factura": r.numero_factura,
                "primer_apellido": r.primer_apellido,
                "segundo_apellido": r.segundo_apellido,
                "primer_nombre": r.primer_nombre,
                "segundo_nombre": r.segundo_nombre,
                "nombre_completo": r.nombre_completo,
                "sexo": r.sexo,
                "nombre_normalizado": r.nombre_normalizado,
            }
            for r in results
        ]
        
        return jsonify({
            "status": "success",
            "data": {
                "registros": data,
                "total": len(data),
            },
            "errors": []
        })
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 400
    except Exception as e:
        logger.exception("Error extrayendo datos")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 500
    finally:
        os.unlink(tmp_path)


# ============================================================================
# ESTADÍSTICAS - SIN USAR TOKENSA
# ============================================================================

@import_facturas_bp.route("/api/import/facturas-stats", methods=["POST"])
def get_facturas_stats():
    """Obtiene estadísticas sin gastar tokens."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontró archivo Excel"]
        }), 400
    
    file = request.files["file"]
    
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name
    
    try:
        stats, _ = genderize_verifier.get_stats(tmp_path)
        
        return jsonify({
            "status": "success",
            "data": {
                "total_excel": stats.total_excel,
                "nombres_unicos": stats.nombres_unicos,
                "cache_hits": stats.cache_hits,
                "api_calls_necesarias": stats.api_calls_necesarias,
            },
            "errors": []
        })
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 400
    except Exception as e:
        logger.exception("Error calculando stats")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 500
    finally:
        os.unlink(tmp_path)


# ============================================================================
# CORREGIR GÉNERO EN CACHE
# ============================================================================

@import_facturas_bp.route("/api/import/cache-corregir", methods=["POST"])
def corregir_genero():
    """Sobrescribe el género de un nombre en el cache."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["JSON inválido"]
        }), 400

    normalized_name = (data.get("nombre_normalizado") or "").strip()
    new_gender = (data.get("genero") or "").strip().lower()

    if not normalized_name:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Falta 'nombre_normalizado'"]
        }), 400

    # Aceptar tanto 'M'/'F' como 'male'/'female'
    if new_gender in ("m", "male"):
        new_gender = "male"
    elif new_gender in ("f", "female"):
        new_gender = "female"
    else:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["'genero' debe ser 'M'/'F' o 'male'/'female'"]
        }), 400

    ok = genderize_service.override_gender(normalized_name, new_gender)
    if not ok:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Nombre '{normalized_name}' no encontrado en cache"]
        }), 404

    return jsonify({
        "status": "success",
        "data": {
            "nombre_normalizado": normalized_name,
            "genero": new_gender,
        },
        "errors": []
    })


# ============================================================================
# VERIFICAR Y COMPARAR - CON USO DE TOKENS
# ============================================================================

@import_facturas_bp.route("/api/import/facturas-verify", methods=["POST"])
def verify_facturas():
    """Verifica sexo del Excel contra API Genderize."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontró archivo Excel"]
        }), 400
    
    file = request.files["file"]
    
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name
    
    try:
        stats, discrepancies = genderize_verifier.verificar_y_comparar(tmp_path)
        
        return jsonify({
            "status": "success",
            "data": {
                "stats": {
                    "total_excel": stats.total_excel,
                    "nombres_unicos": stats.nombres_unicos,
                    "cache_hits": stats.cache_hits,
                    "api_calls_necesarias": stats.api_calls_necesarias,
                },
                "discrepancies": [
                    {
                        "numero_factura": d.numero_factura,
                        "primer_apellido": d.primer_apellido,
                        "segundo_apellido": d.segundo_apellido,
                        "primer_nombre": d.primer_nombre,
                        "segundo_nombre": d.segundo_nombre,
                        "nombre_completo": d.nombre_completo,
                        "nombre_normalizado": d.nombre_normalizado,
                        "sexo_excel": d.sexo_excel,
                        "sexo_api": d.sexo_api,
                    }
                    for d in discrepancies
                ],
                "total_discrepancies": len(discrepancies),
            },
            "errors": []
        })
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 400
    except Exception as e:
        logger.exception("Error verificando")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 500
    finally:
        os.unlink(tmp_path)