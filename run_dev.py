from app import create_app
from config.dev import DevConfig

if __name__ == "__main__":
    app = create_app(DevConfig)
    app.run(
        host=DevConfig.HOST,
        port=DevConfig.PORT,
        debug=DevConfig.DEBUG
    )
