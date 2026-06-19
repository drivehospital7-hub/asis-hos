"""Rutas API para notas técnicas."""

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import (
    eps_contratado_crud,
    procedimiento_crud,
    nota_hoja_crud,
    notas_tecnicas_crud,
    eps_nota_crud,
)
from app.utils.auth import admin_requerido

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ============================================================================
# EPS CONTRATADO
# ============================================================================

@api_bp.route("/eps", methods=["GET"])
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
# RELATIONSHIP: EPS → Procedimientos
# ============================================================================


@api_bp.route("/eps/<int:id>/procedimientos", methods=["GET"])
@admin_requerido
def eps_procedimientos(id):
    """Obtiene procedimientos vinculados a una EPS a través de la cadena.

    Recorre: EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento.
    """
    from sqlalchemy.orm import Session

    db: Session = next(get_db())
    try:
        eps = eps_contratado_crud.get_by_id(db, id)
        if not eps:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe EPS con id: {id}"],
            }), 404

        procedimientos = eps_contratado_crud.get_procedimientos_por_eps(db, id)

        return jsonify({
            "status": "success",
            "data": {
                "eps": eps.to_dict(),
                "procedimientos": procedimientos,
            },
            "errors": [],
        })
    finally:
        db.close()


# ============================================================================
# VINCULAR PROCEDIMIENTO (compuesto)
# ============================================================================


@api_bp.route("/eps/<int:eps_id>/vincular-procedimiento", methods=["POST"])
@admin_requerido
def vincular_procedimiento(eps_id):
    """Vincula un procedimiento a una EPS atómicamente.

    Crea EpsNota + NotasTecnicas en una sola transacción.
    """
    from sqlalchemy.orm import Session

    from app.services.vincular_procedimiento_service import ejecutar

    db: Session = next(get_db())
    try:
        data = request.get_json()

        required = ["id_nota_hoja", "id_procedimiento", "tarifa"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"Campos requeridos: {missing}"],
            }), 400

        # Validate EPS exists — 404 if not
        eps = eps_contratado_crud.get_by_id(db, eps_id)
        if not eps:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe EPS con id: {eps_id}"],
            }), 404

        eps_nota, nt = ejecutar(
            db,
            eps_id=eps_id,
            id_nota_hoja=data["id_nota_hoja"],
            id_procedimiento=data["id_procedimiento"],
            tarifa=data["tarifa"],
        )

        nt_dict = nt.to_dict()
        nt_dict["tarifa"] = nt_dict.pop("tariff")

        return jsonify({
            "status": "success",
            "data": {
                "eps_nota": eps_nota.to_dict(),
                "notas_tecnicas": nt_dict,
            },
            "errors": [],
        }), 201

    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)],
        }), 400
    finally:
        db.close()


# ============================================================================
# PROCEDIMIENTO
# ============================================================================

@api_bp.route("/procedimientos", methods=["GET"])
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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


@api_bp.route("/notas-hoja/<int:id>/dependencias", methods=["GET"])
@admin_requerido
def get_nota_hoja_dependencias(id):
    """Retorna las dependencias de una nota hoja (EPS y procedimientos vinculados)."""
    db: Session = next(get_db())
    try:
        from app.models import EpsContratado, EpsNota, NotasTecnicas, Procedimiento
        
        nota = nota_hoja_crud.get_by_id(db, id)
        if not nota:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"No existe nota hoja con id: {id}"]
            }), 404
        
        # EPS vinculadas via eps_nota
        eps_links = (
            db.query(EpsContratado)
            .join(EpsNota, EpsNota.id_eps_contratado == EpsContratado.id)
            .filter(EpsNota.id_nota_hoja == id)
            .all()
        )
        
        # Procedimientos vinculados via notas_tecnicas
        proc_links = (
            db.query(Procedimiento)
            .join(NotasTecnicas, NotasTecnicas.id_procedimiento == Procedimiento.id)
            .filter(NotasTecnicas.id_nota_hoja == id)
            .all()
        )
        
        return jsonify({
            "status": "success",
            "data": {
                "eps_nota_count": len(eps_links),
                "notas_tecnicas_count": len(proc_links),
                "eps_vinculadas": [{"id": e.id, "cod_contrato": e.cod_contrato, "eps": e.eps} for e in eps_links],
                "procedimientos_vinculados": [{"id": p.id, "cups": p.cups, "procedimiento": p.procedimiento} for p in proc_links],
            },
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/notas-hoja/<int:id>", methods=["DELETE"])
@admin_requerido
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


@api_bp.route("/notas-hoja/<int:id>/vinculaciones", methods=["GET"])
@admin_requerido
def get_nota_hoja_vinculaciones(id):
    """Retorna procedimientos y EPS vinculados a una nota hoja."""
    db: Session = next(get_db())
    try:
        from app.models import EpsContratado, EpsNota, NotasTecnicas, Procedimiento

        nota = nota_hoja_crud.get_by_id(db, id)
        if not nota:
            return jsonify({
                "status": "error", "data": {},
                "errors": [f"No existe nota hoja con id: {id}"]
            }), 404

        # Procedimientos vinculados via notas_tecnicas
        proc_links = (
            db.query(
                NotasTecnicas.id.label("nt_id"),
                Procedimiento.id.label("proc_id"),
                Procedimiento.cups,
                Procedimiento.procedimiento,
                NotasTecnicas.tariff,
            )
            .join(Procedimiento, Procedimiento.id == NotasTecnicas.id_procedimiento)
            .filter(NotasTecnicas.id_nota_hoja == id)
            .all()
        )

        # EPS vinculadas via eps_nota
        eps_links = (
            db.query(EpsNota.id.label("eps_nota_id"), EpsContratado.id, EpsContratado.cod_contrato, EpsContratado.eps)
            .join(EpsContratado, EpsContratado.id == EpsNota.id_eps_contratado)
            .filter(EpsNota.id_nota_hoja == id)
            .all()
        )

        return jsonify({
            "status": "success",
            "data": {
                "nota": nota.to_dict(),
                "procedimientos": [
                    {
                        "nt_id": r.nt_id,
                        "id": r.proc_id,
                        "cups": r.cups,
                        "procedimiento": r.procedimiento,
                        "tarifa": float(r.tariff) if r.tariff else None,
                    }
                    for r in proc_links
                ],
                "eps_vinculadas": [
                    {"eps_nota_id": r.eps_nota_id, "id": r.id, "cod_contrato": r.cod_contrato, "eps": r.eps}
                    for r in eps_links
                ],
            },
            "errors": []
        })
    finally:
        db.close()


@api_bp.route("/notas-hoja/<int:id>/vincular-procedimiento", methods=["POST"])
@admin_requerido
def vincular_procedimiento_a_nota(id):
    """Vincula un procedimiento a una nota hoja (solo NotasTecnicas, sin EPS)."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Request body requerido"]
            }), 400

        id_procedimiento = data.get("id_procedimiento")
        tarifa = data.get("tarifa")

        if not id_procedimiento:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["id_procedimiento es requerido"]
            }), 400

        if tarifa is not None and (not isinstance(tarifa, (int, float)) or tarifa <= 0):
            return jsonify({
                "status": "error", "data": {},
                "errors": ["tarifa debe ser un número positivo"]
            }), 400

        from app.models import NotasTecnicas, Procedimiento

        nota = nota_hoja_crud.get_by_id(db, id)
        if not nota:
            return jsonify({
                "status": "error", "data": {},
                "errors": [f"No existe nota hoja con id: {id}"]
            }), 404

        proc = db.query(Procedimiento).filter(Procedimiento.id == id_procedimiento).first()
        if not proc:
            return jsonify({
                "status": "error", "data": {},
                "errors": [f"No existe procedimiento con id: {id_procedimiento}"]
            }), 400

        nt = NotasTecnicas(
            id_procedimiento=id_procedimiento,
            id_nota_hoja=id,
            tariff=tarifa if tarifa is not None else 0,
        )
        db.add(nt)
        db.commit()

        return jsonify({
            "status": "success",
            "data": {"nt_id": nt.id},
            "errors": []
        }), 201

    except Exception as exc:
        db.rollback()
        logger.exception("Error vinculando procedimiento a nota")
        return jsonify({
            "status": "error", "data": {},
            "errors": [f"Error al vincular: {str(exc)}"]
        }), 400
    finally:
        db.close()


@api_bp.route("/notas-hoja/<int:id>/vincular-eps", methods=["POST"])
@admin_requerido
def vincular_eps_a_nota(id):
    """Vincula una EPS a una nota hoja (crea EpsNota)."""
    db: Session = next(get_db())
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Request body requerido"]
            }), 400

        id_eps_contratado = data.get("id_eps_contratado")
        if not id_eps_contratado:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["id_eps_contratado es requerido"]
            }), 400

        from app.models import EpsContratado, EpsNota

        nota = nota_hoja_crud.get_by_id(db, id)
        if not nota:
            return jsonify({
                "status": "error", "data": {},
                "errors": [f"No existe nota hoja con id: {id}"]
            }), 404

        eps = db.query(EpsContratado).filter(EpsContratado.id == id_eps_contratado).first()
        if not eps:
            return jsonify({
                "status": "error", "data": {},
                "errors": [f"No existe EPS con id: {id_eps_contratado}"]
            }), 400

        existing = db.query(EpsNota).filter(
            EpsNota.id_nota_hoja == id,
            EpsNota.id_eps_contratado == id_eps_contratado,
        ).first()
        if existing:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Esa EPS ya está vinculada a esta nota"]
            }), 400

        en = EpsNota(id_nota_hoja=id, id_eps_contratado=id_eps_contratado)
        db.add(en)
        db.commit()

        return jsonify({
            "status": "success",
            "data": {"eps_nota_id": en.id},
            "errors": []
        }), 201

    except Exception as exc:
        db.rollback()
        logger.exception("Error vinculando EPS a nota")
        return jsonify({
            "status": "error", "data": {},
            "errors": [f"Error al vincular: {str(exc)}"]
        }), 400
    finally:
        db.close()


# ============================================================================
# NOTAS TÉCNICAS
# ============================================================================

@api_bp.route("/notas-tecnicas", methods=["GET"])
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
@admin_requerido
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
