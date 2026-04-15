"""Rutas API para notas técnicas."""

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import (
    eps_contratado_crud,
    procedimiento_crud,
    nota_hoja_crud,
    notas_tecnicas_crud,
    eps_nota_crud
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ============================================================================
# EPS CONTRATADO
# ============================================================================

@api_bp.route("/eps", methods=["GET"])
def list_eps():
    """Lista todas las EPS contratadas."""
    db: Session = next(get_db())
    try:
        items = eps_contratado_crud.get_all(db)
        return jsonify({
            "status": "success",
            "data": [e.to_dict() for e in items],
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/eps/<int:id>", methods=["GET"])
def get_eps(id):
    """Obtiene EPS por ID."""
    db: Session = next(get_db())
    try:
        item = eps_contratado_crud.get_by_id(db, id)
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe EPS con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/eps", methods=["POST"])
def create_eps():
    """Crea nueva EPS contratada."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        
        required = ["cod_contrato", "eps"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"Campos requeridos: {missing}"]
            }), 400
        
        item = eps_contratado_crud.create(
            db,
            cod_contrato=data["cod_contrato"],
            eps=data["eps"],
            regimen=data.get("regimen", "SUBSIDIADO")
        )
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 400
    finally:
        db.close()


@api_bp.route("/eps/<int:id>", methods=["PUT"])
def update_eps(id):
    """Actualiza EPS contratada."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        item = eps_contratado_crud.update(db, id, **data)
        
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe EPS con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/eps/<int:id>", methods=["DELETE"])
def delete_eps(id):
    """Elimina EPS contratada."""
    db: Session = next(get_db())
    try:
        deleted = eps_contratado_crud.delete(db, id)
        
        if not deleted:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe EPS con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": {},
            "errors": []
        })
    finally:
        db.close()


# ============================================================================
# PROCEDIMIENTO
# ============================================================================

@api_bp.route("/procedimientos", methods=["GET"])
def list_procedimientos():
    """Lista todos los procedimientos."""
    db: Session = next(get_db())
    try:
        items = procedimiento_crud.get_all(db)
        return jsonify({
            "status": "success",
            "data": [p.to_dict() for p in items],
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/procedimientos/<int:id>", methods=["GET"])
def get_procedimiento(id):
    """Obtiene procedimiento por ID."""
    db: Session = next(get_db())
    try:
        item = procedimiento_crud.get_by_id(db, id)
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe procedimiento con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/procedimientos", methods=["POST"])
def create_procedimiento():
    """Crea nuevo procedimiento."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        
        required = ["cups", "procedimiento"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"Campos requeridos: {missing}"]
            }), 400
        
        item = procedimiento_crud.create(
            db,
            cups=data["cups"],
            procedimiento=data["procedimiento"]
        )
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 400
    finally:
        db.close()


@api_bp.route("/procedimientos/<int:id>", methods=["PUT"])
def update_procedimiento(id):
    """Actualiza procedimiento."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        item = procedimiento_crud.update(db, id, **data)
        
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe procedimiento con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/procedimientos/<int:id>", methods=["DELETE"])
def delete_procedimiento(id):
    """Elimina procedimiento."""
    db: Session = next(get_db())
    try:
        deleted = procedimiento_crud.delete(db, id)
        
        if not deleted:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe procedimiento con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": {},
            "errors": []
        })
    finally:
        db.close()


# ============================================================================
# NOTA HOJA
# ============================================================================

@api_bp.route("/notas-hoja", methods=["GET"])
def list_notas_hoja():
    """Lista todas las notas hojas."""
    db: Session = next(get_db())
    try:
        items = nota_hoja_crud.get_all(db)
        return jsonify({
            "status": "success",
            "data": [n.to_dict() for n in items],
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/notas-hoja/<int:id>", methods=["GET"])
def get_nota_hoja(id):
    """Obtiene nota hoja por ID."""
    db: Session = next(get_db())
    try:
        item = nota_hoja_crud.get_by_id(db, id)
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe nota hoja con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/notas-hoja", methods=["POST"])
def create_nota_hoja():
    """Crea nueva nota hoja."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        
        if "nota" not in data:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": ["Campo requerido: nota"]
            }), 400
        
        item = nota_hoja_crud.create(db, nota=data["nota"])
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 400
    finally:
        db.close()


@api_bp.route("/notas-hoja/<int:id>", methods=["PUT"])
def update_nota_hoja(id):
    """Actualiza nota hoja."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        item = nota_hoja_crud.update(db, id, **data)
        
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe nota hoja con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/notas-hoja/<int:id>", methods=["DELETE"])
def delete_nota_hoja(id):
    """Elimina nota hoja."""
    db: Session = next(get_db())
    try:
        deleted = nota_hoja_crud.delete(db, id)
        
        if not deleted:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe nota hoja con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": {},
            "errors": []
        })
    finally:
        db.close()


# ============================================================================
# NOTAS TÉCNICAS
# ============================================================================

@api_bp.route("/notas-tecnicas", methods=["GET"])
def list_notas_tecnicas():
    """Lista todas las notas técnicas."""
    db: Session = next(get_db())
    try:
        items = notas_tecnicas_crud.get_all(db)
        return jsonify({
            "status": "success",
            "data": [n.to_dict() for n in items],
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/notas-tecnicas/<int:id>", methods=["GET"])
def get_nota_tecnica(id):
    """Obtiene nota técnica por ID."""
    db: Session = next(get_db())
    try:
        item = notas_tecnicas_crud.get_by_id(db, id)
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe nota técnica con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/notas-tecnicas", methods=["POST"])
def create_nota_tecnica():
    """Crea nueva nota técnica."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        
        required = ["id_procedimiento", "id_nota_hoja", "tarifa"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"Campos requeridos: {missing}"]
            }), 400
        
        item = notas_tecnicas_crud.create(
            db,
            id_procedimiento=data["id_procedimiento"],
            id_nota_hoja=data["id_nota_hoja"],
            tarifa=data["tarifa"]
        )
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 400
    finally:
        db.close()


@api_bp.route("/notas-tecnicas/<int:id>", methods=["PUT"])
def update_nota_tecnica(id):
    """Actualiza nota técnica."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        item = notas_tecnicas_crud.update(db, id, **data)
        
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe nota técnica con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/notas-tecnicas/<int:id>", methods=["DELETE"])
def delete_nota_tecnica(id):
    """Elimina nota técnica."""
    db: Session = next(get_db())
    try:
        deleted = notas_tecnicas_crud.delete(db, id)
        
        if not deleted:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe nota técnica con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": {},
            "errors": []
        })
    finally:
        db.close()


# ============================================================================
# EPS NOTA
# ============================================================================

@api_bp.route("/eps-nota", methods=["GET"])
def list_eps_nota():
    """Lista todas las relaciones EPS-Nota."""
    db: Session = next(get_db())
    try:
        items = eps_nota_crud.get_all(db)
        return jsonify({
            "status": "success",
            "data": [e.to_dict() for e in items],
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/eps-nota/<int:id>", methods=["GET"])
def get_eps_nota(id):
    """Obtiene relación EPS-Nota por ID."""
    db: Session = next(get_db())
    try:
        item = eps_nota_crud.get_by_id(db, id)
        if not item:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe relación EPS-Nota con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/eps-nota", methods=["POST"])
def create_eps_nota():
    """Crea nueva relación EPS-Nota."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        
        required = ["id_nota_hoja", "id_eps_contratado"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"Campos requeridos: {missing}"]
            }), 400
        
        item = eps_nota_crud.create(
            db,
            id_nota_hoja=data["id_nota_hoja"],
            id_eps_contratado=data["id_eps_contratado"]
        )
        
        return jsonify({
            "status": "success",
            "data": item.to_dict(),
            "errors": []
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 400
    finally:
        db.close()


@api_bp.route("/eps-nota/<int:id>", methods=["DELETE"])
def delete_eps_nota(id):
    """Elimina relación EPS-Nota."""
    db: Session = next(get_db())
    try:
        deleted = eps_nota_crud.delete(db, id)
        
        if not deleted:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe relación EPS-Nota con id: {id}"]
            }), 404
        
        return jsonify({
            "status": "success",
            "data": {},
            "errors": []
        })
    finally:
        db.close()
