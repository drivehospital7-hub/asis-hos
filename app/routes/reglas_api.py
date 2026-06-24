"""REST API for Rule Engine management.

Blueprint: reglas_api, url_prefix=/api
All endpoints return canonical {"status","data","errors"} envelope.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

from app.database import get_db
from app.services.reglas.rule_service import (
    create_rule,
    delete_rule,
    get_rule,
    list_rules,
    list_versions,
    create_version,
    update_rule,
)
from app.services.reglas.exception_service import list_exceptions, create_exception
from app.services.reglas.evidence_service import query_evidence
from app.services.reglas.audit_service import query_audit
from app.services.reglas.simulator_service import simulate
from app.utils.auth import admin_requerido

logger = logging.getLogger(__name__)

reglas_api_bp = Blueprint("reglas_api", __name__, url_prefix="/api")


# ─── Rules CRUD ─────────────────────────────────────────────────────


@reglas_api_bp.route("/reglas", methods=["GET"])
@admin_requerido
def api_list_rules():
    """List rules with optional filters: ?dominio=, ?estado=, ?activo="""
    db = next(get_db())
    try:
        dominio = request.args.get("dominio")
        estado = request.args.get("estado")
        activo_str = request.args.get("activo")
        activo = None
        if activo_str is not None:
            activo = activo_str.lower() in ("true", "1", "yes")

        items = list_rules(db, dominio=dominio, estado=estado, activo=activo)
        return jsonify({"status": "success", "data": items, "errors": []})
    except Exception as exc:
        logger.exception("Error listing rules")
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


@reglas_api_bp.route("/reglas/<int:regla_id>", methods=["GET"])
@admin_requerido
def api_get_rule(regla_id: int):
    """Get rule detail with nested condition tree and exceptions."""
    db = next(get_db())
    try:
        rule = get_rule(db, regla_id)
        if rule is None:
            return jsonify({
                "status": "error", "data": {},
                "errors": [f"Regla {regla_id} no encontrada"],
            }), 404
        return jsonify({"status": "success", "data": rule, "errors": []})
    except Exception as exc:
        logger.exception("Error getting rule %s", regla_id)
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


@reglas_api_bp.route("/reglas", methods=["POST"])
@admin_requerido
def api_create_rule():
    """Create a new rule (draft, version=1)."""
    db = next(get_db())
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Request body requerido"],
            }), 400

        # Validate required field
        if "nombre" not in data or not data["nombre"]:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Campo requerido: nombre"],
            }), 400

        rule = create_rule(db, data)
        return jsonify({"status": "success", "data": rule, "errors": []}), 201
    except ValueError as e:
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 400
    except Exception as exc:
        logger.exception("Error creating rule")
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


@reglas_api_bp.route("/reglas/<int:regla_id>", methods=["PUT"])
@admin_requerido
def api_update_rule(regla_id: int):
    """Update rule with auto-versioning (deprecates old, creates new)."""
    db = next(get_db())
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Request body requerido"],
            }), 400

        result = update_rule(db, regla_id, data)
        return jsonify({"status": "success", "data": result, "errors": []})
    except ValueError as e:
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 400
    except Exception as exc:
        logger.exception("Error updating rule %s", regla_id)
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


@reglas_api_bp.route("/reglas/<int:regla_id>", methods=["DELETE"])
@admin_requerido
def api_delete_rule(regla_id: int):
    """Soft-delete rule (estado=retired)."""
    db = next(get_db())
    try:
        delete_rule(db, regla_id)
        return jsonify({"status": "success", "data": {}, "errors": []})
    except ValueError as e:
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 400
    except Exception as exc:
        logger.exception("Error deleting rule %s", regla_id)
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


# ─── Versions ────────────────────────────────────────────────────────


@reglas_api_bp.route("/reglas/<int:regla_id>/versiones", methods=["GET"])
@admin_requerido
def api_list_versions(regla_id: int):
    """List all versions of a rule (ordered DESC)."""
    db = next(get_db())
    try:
        versions = list_versions(db, regla_id)
        return jsonify({"status": "success", "data": versions, "errors": []})
    except Exception as exc:
        logger.exception("Error listing versions for rule %s", regla_id)
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


@reglas_api_bp.route("/reglas/<int:regla_id>/versionar", methods=["POST"])
@admin_requerido
def api_create_version(regla_id: int):
    """Clone active rule as a new draft version."""
    db = next(get_db())
    try:
        new_version = create_version(db, regla_id)
        return jsonify({"status": "success", "data": new_version, "errors": []}), 201
    except ValueError as e:
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 400
    except Exception as exc:
        logger.exception("Error versioning rule %s", regla_id)
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


# ─── Exceptions ──────────────────────────────────────────────────────


@reglas_api_bp.route("/reglas/<int:regla_id>/excepciones", methods=["GET"])
@admin_requerido
def api_list_exceptions(regla_id: int):
    """List all exceptions for a rule."""
    db = next(get_db())
    try:
        items = list_exceptions(db, regla_id)
        return jsonify({"status": "success", "data": items, "errors": []})
    except Exception as exc:
        logger.exception("Error listing exceptions for rule %s", regla_id)
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


@reglas_api_bp.route("/reglas/<int:regla_id>/excepciones", methods=["POST"])
@admin_requerido
def api_create_exception(regla_id: int):
    """Create a new exception for a rule."""
    db = next(get_db())
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Request body requerido"],
            }), 400

        item = create_exception(db, regla_id, data)
        return jsonify({"status": "success", "data": item, "errors": []}), 201
    except ValueError as e:
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 400
    except Exception as exc:
        logger.exception("Error creating exception for rule %s", regla_id)
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


# ─── Evidence & Audit ────────────────────────────────────────────────


@reglas_api_bp.route("/evidencias", methods=["GET"])
@admin_requerido
def api_query_evidence():
    """Query evidence records with filters and pagination."""
    db = next(get_db())
    try:
        regla_id = request.args.get("regla_id", type=int)
        factura = request.args.get("factura")
        dominio = request.args.get("dominio")
        outcome = request.args.get("outcome")
        desde = request.args.get("desde")
        hasta = request.args.get("hasta")
        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)

        result = query_evidence(
            db,
            regla_id=regla_id,
            factura=factura,
            dominio=dominio,
            outcome=outcome,
            desde=desde,
            hasta=hasta,
            limit=limit,
            offset=offset,
        )
        return jsonify({"status": "success", "data": result, "errors": []})
    except Exception as exc:
        logger.exception("Error querying evidence")
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


@reglas_api_bp.route("/auditoria", methods=["GET"])
@admin_requerido
def api_query_audit():
    """Query audit results with filters and pagination."""
    db = next(get_db())
    try:
        regla_id = request.args.get("regla_id", type=int)
        factura = request.args.get("factura")
        resultado = request.args.get("resultado")
        desde = request.args.get("desde")
        hasta = request.args.get("hasta")
        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)

        result = query_audit(
            db,
            regla_id=regla_id,
            factura=factura,
            resultado=resultado,
            desde=desde,
            hasta=hasta,
            limit=limit,
            offset=offset,
        )
        return jsonify({"status": "success", "data": result, "errors": []})
    except Exception as exc:
        logger.exception("Error querying audit")
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


# ─── Simulator ────────────────────────────────────────────────────────


@reglas_api_bp.route("/reglas/simular", methods=["POST"])
@admin_requerido
def api_simulate():
    """Dry-run: compare engine vs legacy detectors on uploaded Excel."""
    db = next(get_db())
    try:
        if "file" not in request.files:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Campo requerido: file (archivo Excel)"],
            }), 400

        file_storage = request.files["file"]
        if not file_storage.filename:
            return jsonify({
                "status": "error", "data": {},
                "errors": ["Archivo no seleccionado"],
            }), 400

        rule_name = request.form.get("rule_name")

        result = simulate(db, file_storage, rule_name=rule_name)
        return jsonify({"status": "success", "data": result, "errors": []})
    except ValueError as e:
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 400
    except Exception as exc:
        logger.exception("Error running simulator")
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
    finally:
        db.close()


@reglas_api_bp.route("/evidencias", methods=["DELETE"])
@admin_requerido
def api_clear_evidence():
    """Delete all evidence and audit records (testing only)."""
    from app.database import _get_engine
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("TRUNCATE TABLE resultados_auditoria, evidencias"))
            conn.commit()
        logger.warning("All evidence and audit records truncated (testing cleanup)")
        return jsonify({"status": "success", "data": {"message": "Datos de evidencia y auditoria eliminados"}, "errors": []})
    except Exception as exc:
        logger.exception("Error clearing evidence data")
        return jsonify({"status": "error", "data": {}, "errors": [str(exc)]}), 500
