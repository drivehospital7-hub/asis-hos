from flask import Flask

def create_app():
    app = Flask(__name__)

    from app.routes.facturas import facturas_bp
    app.register_blueprint(facturas_bp)

    return app