"""Routes de autenticación (login/logout)."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, AREAS_VALIDAS

auth_bp = Blueprint("auth", __name__)

# Mapeo de áreas a endpoints
AREA_ENDPOINT_MAP = {
    "odontologia": "excel_headers.excel_headers_page",
    "urgencias": "urgencias.urgencias_page",
    "derechos": "derechos.derechos_page",
    "equipos_basicos": "ordenado_facturado.ordenado_facturado_page",
}


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Página de login."""
    # Si ya está logueado, redirigir al home
    if current_user.is_authenticated:
        return redirect(url_for("control_errores.control_errores_page"))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Usuario y contraseña son requeridos", "error")
            return render_template("login.html")
        
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash(f"Bienvenido {user.username}", "success")
                
                # Redirigir al área por defecto o la primera permitida
                next_page = request.args.get("next")
                if next_page:
                    return redirect(next_page)
                
                if user.rol == "admin":
                    return redirect(url_for("control_errores.control_errores_page"))
                elif user.areas:
                    # Redirigir a la primera área permitida
                    area = user.areas[0].area
                    endpoint = AREA_ENDPOINT_MAP.get(area, "home.home_page")
                    return redirect(url_for(endpoint))
                else:
                    return redirect(url_for("control_errores.control_errores_page"))
            else:
                flash("Usuario o contraseña incorrectos", "error")
        finally:
            db.close()
    
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Cerrar sesión."""
    logout_user()
    flash("Sesión cerrada", "success")
    return redirect(url_for("control_errores.control_errores_page"))


@auth_bp.route("/usuarios")
@login_required
def listar_usuarios():
    """Listar usuarios (solo admin)."""
    if current_user.rol != "admin":
        flash("Acceso denegado", "error")
        return redirect(url_for("control_errores.control_errores_page"))
    
    db: Session = SessionLocal()
    try:
        usuarios = db.query(User).all()
        return render_template("usuarios.html", usuarios=usuarios, areas_validas=AREAS_VALIDAS)
    finally:
        db.close()


@auth_bp.route("/usuarios/crear", methods=["POST"])
@login_required
def crear_usuario():
    """Crear usuario (solo admin)."""
    if current_user.rol != "admin":
        flash("Acceso denegado", "error")
        return redirect(url_for("control_errores.control_errores_page"))
    
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    rol = request.form.get("rol", "usuario")
    areas = request.form.getlist("areas")
    
    if not username or not password:
        flash("Usuario y contraseña son requeridos", "error")
        return redirect(url_for("auth.listar_usuarios"))
    
    if rol != "admin" and not areas:
        flash("Debe seleccionar al menos un área", "error")
        return redirect(url_for("auth.listar_usuarios"))
    
    db: Session = SessionLocal()
    try:
        # Verificar si existe
        existentes = db.query(User).filter(User.username == username).first()
        if existentes:
            flash(f"El usuario {username} ya existe", "error")
            return redirect(url_for("auth.listar_usuarios"))
        
        # Crear usuario
        password_hash = generate_password_hash(password)
        nuevo_usuario = User(username=username, password_hash=password_hash, rol=rol)
        db.add(nuevo_usuario)
        db.flush()  # Obtener ID
        
        # Agregar áreas
        if rol != "admin":
            for area in areas:
                if area in AREAS_VALIDAS:
                    db.add(UserArea(user_id=nuevo_usuario.id, area=area))
        
        db.commit()
        flash(f"Usuario {username} creado", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
    finally:
        db.close()
    
    return redirect(url_for("auth.listar_usuarios"))


# Importar UserArea aquí para evitar circular import
from app.models import UserArea