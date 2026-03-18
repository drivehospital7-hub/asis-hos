from flask import Blueprint

facturas_bp = Blueprint("facturas", __name__)

@facturas_bp.route("/")
def home():
    return "API de facturas funcionando 🚀"