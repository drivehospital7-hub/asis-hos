import logging

from flask import Blueprint, redirect, render_template, url_for

logger = logging.getLogger(__name__)

home_bp = Blueprint("home", __name__)


@home_bp.get("/")
def root_redirect():
    """Redirige la raíz al dashboard."""
    return redirect(url_for("home.home_page"))


@home_bp.get("/dashboard")
def home_page():
    """Pagina principal con las areas de trabajo."""
    return render_template("home.html")