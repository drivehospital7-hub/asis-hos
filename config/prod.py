import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _prod_secret_key() -> str:
    """Resuelve SECRET_KEY para producción: env var > instance/secret.key.

    Si no hay SECRET_KEY en env ni en el archivo, error CRÍTICO.
    instance/secret.key es inmune a git pull — está en .gitignore.
    """
    key = os.getenv("SECRET_KEY")
    if key:
        return key

    key_path = Path("instance/secret.key")
    if key_path.exists():
        return key_path.read_text().strip()

    raise ValueError(
        "SECRET_KEY no encontrada. "
        "Setear en .env, variable de entorno, o crear instance/secret.key"
    )


class ProdConfig:
    DEBUG = False
    TESTING = False

    HOST = os.getenv("PROD_HOST", "0.0.0.0")
    PORT = int(os.getenv("PROD_PORT", 5001))

    SECRET_KEY = _prod_secret_key()

    MAX_CONTENT_LENGTH = None  # Sin límite de tamaño

    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/prod.log"

    @classmethod
    def validate(cls):
        """Validate config before using in production."""
        # _prod_secret_key() ya valida SECRET_KEY al cargar la clase
        if not os.getenv("DB_HOST"):
            raise ValueError("DB_HOST must be set in production environment")
