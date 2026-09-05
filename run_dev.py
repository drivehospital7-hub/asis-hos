import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Agregar path de librerías linuxbrew para psycopg2
linuxbrew_lib = "/home/linuxbrew/.linuxbrew/lib"
if linuxbrew_lib not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = linuxbrew_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

from app import create_app
from config.dev import DevConfig

if __name__ == "__main__":
    # Asegurar que el directorio de logs existe
    os.makedirs("logs", exist_ok=True)

    # Configurar logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Solo errores a archivo
    error_handler = logging.FileHandler('logs/error.log', mode='w')
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Consola solo errores
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.ERROR)
    
    logger.addHandler(error_handler)
    logger.addHandler(stream_handler)
    
    app = create_app(DevConfig)
    app.run(
        host=DevConfig.HOST,
        port=DevConfig.PORT,
        debug=DevConfig.DEBUG
    )
