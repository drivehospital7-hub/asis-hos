import os
from dotenv import load_dotenv

load_dotenv()


class ProdConfig:
    DEBUG = False
    TESTING = False
    
    HOST = os.getenv("PROD_HOST", "0.0.0.0")
    PORT = int(os.getenv("PROD_PORT", 5001))
    
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    MAX_CONTENT_LENGTH = None  # Sin límite de tamaño
    
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/prod.log"
    
    @classmethod
    def validate(cls):
        """Validate config before using in production."""
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in production environment")
