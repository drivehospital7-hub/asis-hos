from flask import Flask


def create_app(config=None):
    app = Flask(__name__)
    
    if config:
        app.config.from_object(config)
    
    from app.routes.excel_headers import excel_headers_bp
    
    app.register_blueprint(excel_headers_bp)
    
    return app
