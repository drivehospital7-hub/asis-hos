from flask import Flask

def create_app():
    app = Flask(__name__)

    from app.routes.excel_headers import excel_headers_bp
    from app.routes.facturas import facturas_bp

    app.register_blueprint(facturas_bp)
    app.register_blueprint(excel_headers_bp, url_prefix="/excel")

    return app