"""Ruta para extraer nombres del Excel."""

import json
import logging
import os
import tempfile
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session
from sqlalchemy.orm import Session
from urllib.error import HTTPError

from app.database import get_db
from app.services import genderize_extractor, genderize_service, genderize_verifier
from app.utils.auth import admin_requerido

logger = logging.getLogger(__name__)

import_facturas_bp = Blueprint("import_facturas", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@import_facturas_bp.route("/import-facturas")
@admin_requerido
def import_facturas_react():
    """React shell for Genderize / Import Facturas."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/genderize/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_shell.html",
        page_title="Verificar Sexo — Genderize",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )




@import_facturas_bp.route("/api/import/facturas-nombres", methods=["POST"])
@admin_requerido
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
        total_raw = len(results)
        
        # Deduplicar por factura (un paciente por factura)
        facturas = {}
        for r in results:
            if r.numero_factura not in facturas:
                facturas[r.numero_factura] = r
        unique_results = list(facturas.values())
        
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
            for r in unique_results
        ]
        
        return jsonify({
            "status": "success",
            "data": {
                "registros": data,
                "total": len(data),
                "total_raw": total_raw,
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
    except HTTPError as e:
        logger.warning("HTTP %d en genderize: %s", e.code, str(e)[:200])
        if e.code == 429:
            msg = "La API Genderize tiene un límite de solicitudes. Esperá unos minutos y probá de nuevo."
        else:
            msg = f"Error HTTP {e.code} al consultar Genderize. Intentá de nuevo más tarde."
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [msg]
        }), 429 if e.code == 429 else 502
    except Exception as e:
        logger.exception("Error verificando")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 500
    finally:
        os.unlink(tmp_path)