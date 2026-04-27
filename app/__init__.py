from flask import Flask
from flask_login import LoginManager

login_manager = LoginManager()


def create_app(config=None):
    app = Flask(__name__)
    
    if config:
        app.config.from_object(config)
    
    # Inicializar Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # Route para login
    
    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == int(user_id)).first()
        finally:
            db.close()
    
    from app.routes.home import home_bp
    from app.routes.excel_headers import excel_headers_bp
    from app.routes.urgencias import urgencias_bp
    from app.routes.procedimientos import procedimientos_bp
    from app.routes.ordenado_facturado import ordenado_facturado_bp
    from app.routes.notas_api import api_bp
    from app.routes.import_csv import import_csv_bp
    from app.routes.derechos import derechos_bp
    from app.routes.auth import auth_bp
    
    # Home debe ser la raíz
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(excel_headers_bp, url_prefix="/odontologia")
    app.register_blueprint(urgencias_bp, url_prefix="/urgencias")
    app.register_blueprint(procedimientos_bp)
    app.register_blueprint(ordenado_facturado_bp, url_prefix="/ordenado-facturado")
    app.register_blueprint(api_bp)
    app.register_blueprint(import_csv_bp)
    app.register_blueprint(derechos_bp, url_prefix="/derechos")
    
    return app
