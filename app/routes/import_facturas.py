"""Ruta para extraer nombres del Excel."""

import logging
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import genderize_extractor, genderize_verifier

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
                "primer_nombre": r.primer_nombre,
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
                        "primer_nombre": d.primer_nombre,
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