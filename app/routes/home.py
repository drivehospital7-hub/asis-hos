import logging

from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

home_bp = Blueprint("home", __name__)


@home_bp.get("/")
def home_page():
    """Pagina principal con las áreas de trabajo."""
    return render_template("home.html")