"""Ruta para importación masiva de datos via CSV."""

import logging
from pathlib import Path

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import (
    eps_contratado_crud,
    procedimiento_crud,
    nota_hoja_crud,
    notas_tecnicas_crud,
    eps_nota_crud,
    genderize_extractor
)

import_csv_bp = Blueprint("import_csv", __name__, url_prefix="/api/import")


def parse_csv(content: str) -> list[dict]:
    """Parsea contenido CSV a lista de diccionarios."""
    lines = content.strip().split("\n")
    if not lines:
        return []
    
    # Primera línea = headers
    headers = [h.strip() for h in lines[0].split(",")]
    
    # Resto = datos
    result = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(",")]
        row = dict(zip(headers, values))
        result.append(row)
    
    return result


# ============================================================================
# EPS CONTRATADO
# ============================================================================

@import_csv_bp.route("/eps", methods=["POST"])
def import_eps():
    """Importa EPS desde CSV."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontró archivo CSV"]
        }), 400
    
    file = request.files["file"]
    content = file.read().decode("utf-8")
    
    try:
        data = parse_csv(content)
    except Exception as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error parseando CSV: {str(e)}"]
        }), 400
    
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["CSV vacío o sin datos"]
        }), 400
    
    db: Session = next(get_db())
    imported = 0
    errors = []
    
    try:
        for row in data:
            try:
                eps_contratado_crud.create(
                    db,
                    cod_contrato=row["cod_contrato"],
                    eps=row["eps"],
                    regimen=row.get("regimen", "SUBSIDIADO")
                )
                imported += 1
            except ValueError as e:
                errors.append(f"Fila {row}: {str(e)}")
            except KeyError as e:
                errors.append(f"Fila {row}: falta campo {str(e)}")
        
        return jsonify({
            "status": "success",
            "data": {"imported": imported},
            "errors": errors
        })
    finally:
        db.close()


# ============================================================================
# PROCEDIMIENTO
# ============================================================================

@import_csv_bp.route("/procedimientos", methods=["POST"])
def import_procedimientos():
    """Importa procedimientos desde CSV."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontró archivo CSV"]
        }), 400
    
    file = request.files["file"]
    content = file.read().decode("utf-8")
    
    try:
        data = parse_csv(content)
    except Exception as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error parseando CSV: {str(e)}"]
        }), 400
    
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["CSV vacío o sin datos"]
        }), 400
    
    db: Session = next(get_db())
    imported = 0
    errors = []
    
    try:
        for row in data:
            try:
                procedimiento_crud.create(
                    db,
                    cups=row["cups"],
                    procedimiento=row["procedimiento"]
                )
                imported += 1
            except ValueError as e:
                errors.append(f"Fila {row}: {str(e)}")
            except KeyError as e:
                errors.append(f"Fila {row}: falta campo {str(e)}")
        
        return jsonify({
            "status": "success",
            "data": {"imported": imported},
            "errors": errors
        })
    finally:
        db.close()


# ============================================================================
# NOTA HOJA
# ============================================================================

@import_csv_bp.route("/notas-hoja", methods=["POST"])
def import_notas_hoja():
    """Importa notas hoja desde CSV."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontró archivo CSV"]
        }), 400
    
    file = request.files["file"]
    content = file.read().decode("utf-8")
    
    try:
        data = parse_csv(content)
    except Exception as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error parseando CSV: {str(e)}"]
        }), 400
    
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["CSV vacío o sin datos"]
        }), 400
    
    db: Session = next(get_db())
    imported = 0
    errors = []
    
    try:
        for row in data:
            try:
                nota_hoja_crud.create(
                    db,
                    nota=row["nota"]
                )
                imported += 1
            except ValueError as e:
                errors.append(f"Fila {row}: {str(e)}")
            except KeyError as e:
                errors.append(f"Fila {row}: falta campo {str(e)}")
        
        return jsonify({
            "status": "success",
            "data": {"imported": imported},
            "errors": errors
        })
    finally:
        db.close()


# ============================================================================
# NOTAS TÉCNICAS
# ============================================================================

@import_csv_bp.route("/notas-tecnicas", methods=["POST"])
def import_notas_tecnicas():
    """Importa notas técnicas desde CSV."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontró archivo CSV"]
        }), 400
    
    file = request.files["file"]
    content = file.read().decode("utf-8")
    
    try:
        data = parse_csv(content)
    except Exception as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error parseando CSV: {str(e)}"]
        }), 400
    
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["CSV vacío o sin datos"]
        }), 400
    
    db: Session = next(get_db())
    imported = 0
    errors = []
    
    try:
        for row in data:
            try:
                notas_tecnicas_crud.create(
                    db,
                    id_procedimiento=int(row["id_procedimiento"]),
                    id_nota_hoja=int(row["id_nota_hoja"]),
                    tarifa=float(row["tarifa"])
                )
                imported += 1
            except ValueError as e:
                errors.append(f"Fila {row}: {str(e)}")
            except KeyError as e:
                errors.append(f"Fila {row}: falta campo {str(e)}")
        
        return jsonify({
            "status": "success",
            "data": {"imported": imported},
            "errors": errors
        })
    finally:
        db.close()


# ============================================================================
# EPS NOTA
# ============================================================================

@import_csv_bp.route("/eps-nota", methods=["POST"])
def import_eps_nota():
    """Importa relaciones EPS-Nota desde CSV."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontró archivo CSV"]
        }), 400
    
    file = request.files["file"]
    content = file.read().decode("utf-8")
    
    try:
        data = parse_csv(content)
    except Exception as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error parseando CSV: {str(e)}"]
        }), 400
    
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["CSV vacío o sin datos"]
        }), 400
    
    db: Session = next(get_db())
    imported = 0
    errors = []
    
    try:
        for row in data:
            try:
                eps_nota_crud.create(
                    db,
                    id_nota_hoja=int(row["id_nota_hoja"]),
                    id_eps_contratado=int(row["id_eps_contratado"])
                )
                imported += 1
            except ValueError as e:
                errors.append(f"Fila {row}: {str(e)}")
            except KeyError as e:
                errors.append(f"Fila {row}: falta campo {str(e)}")
        
        return jsonify({
            "status": "success",
            "data": {"imported": imported},
            "errors": errors
        })
    finally:
        db.close()
