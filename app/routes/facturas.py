from flask import Blueprint

facturas_bp = Blueprint("facturas", __name__)


@facturas_bp.route("/")
def home():
    """Health check endpoint."""
    return {"status": "success", "data": {"message": "API running"}, "errors": []}