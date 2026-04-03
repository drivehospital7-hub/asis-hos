from waitress import serve
from app import create_app
from config.prod import ProdConfig


def main():
    # Validate config before starting
    ProdConfig.validate()
    
    app = create_app(ProdConfig)
    
    print(f"Starting production server on {ProdConfig.HOST}:{ProdConfig.PORT}")
    print("Access from network at: http://<your-ip>:{}/".format(ProdConfig.PORT))
    
    serve(app, host=ProdConfig.HOST, port=ProdConfig.PORT)


if __name__ == "__main__":
    main()
