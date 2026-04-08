import os


class DevConfig:
    DEBUG = True
    TESTING = False
    
    HOST = os.getenv("DEV_HOST", "127.0.0.1")
    PORT = int(os.getenv("DEV_PORT", 5000))
    
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
    
    MAX_CONTENT_LENGTH = None  # Sin límite de tamaño
    
    LOG_LEVEL = "DEBUG"
    LOG_FILE = "logs/dev.log"
