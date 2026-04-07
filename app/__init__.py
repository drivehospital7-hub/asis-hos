from flask import Flask


def create_app(config=None):
    app = Flask(__name__)
    
    if config:
        app.config.from_object(config)
    
    from app.routes.home import home_bp
    from app.routes.excel_headers import excel_headers_bp
    
    # Home debe ser la raíz
    app.register_blueprint(home_bp)
    app.register_blueprint(excel_headers_bp, url_prefix="/odontologia")
    
    return app
