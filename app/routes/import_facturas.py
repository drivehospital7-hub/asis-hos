"""Ruta para extraer nombres del Excel."""

import logging
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import genderize_extractor

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