import os


class DevConfig:
    DEBUG = True
    TESTING = False
    
    HOST = os.getenv("DEV_HOST", "127.0.0.1")
    PORT = int(os.getenv("DEV_PORT", 5000))
    
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
    
    # Límite de 50MB para uploads (proteger contra archivos gigante)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    LOG_LEVEL = "DEBUG"
    LOG_FILE = "logs/dev.log"
