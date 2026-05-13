import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _prod_secret_key() -> str:
    """Resuelve SECRET_KEY: env var > instance/secret.key > generar y persistir.

    En el peor caso genera una clave nueva y la guarda en instance/secret.key.
    Ese archivo está en .gitignore — git pull nunca lo toca.
    """
    key = os.getenv("SECRET_KEY")
    if key:
        return key

    key_path = Path("instance/secret.key")
    if key_path.exists():
        return key_path.read_text().strip()

    # Primera ejecución: generar, persistir, y devolver
    new_key = secrets.token_hex(32)
    try:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(new_key)
    except OSError:
        pass  # Si no puede escribir, la clave en memoria es suficiente
    return new_key


class ProdConfig:
    DEBUG = False
    TESTING = False

    HOST = os.getenv("PROD_HOST", "0.0.0.0")
    PORT = int(os.getenv("PROD_PORT", 5001))

    SECRET_KEY = _prod_secret_key()

    MAX_CONTENT_LENGTH = None  # Sin límite de tamaño

    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/prod.log"
