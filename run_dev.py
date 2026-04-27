import os
import logging

# Agregar path de librerías linuxbrew para psycopg2
linuxbrew_lib = "/home/linuxbrew/.linuxbrew/lib"
if linuxbrew_lib not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = linuxbrew_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

from app import create_app
from config.dev import DevConfig

class LevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno == self.level

if __name__ == "__main__":
    # Configurar logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Handlers para archivos separados
    debug_handler = logging.FileHandler('logs/debug.log', mode='w')
    debug_handler.setFormatter(formatter)
    debug_handler.addFilter(LevelFilter(logging.DEBUG))
    
    info_handler = logging.FileHandler('logs/info.log', mode='w')
    info_handler.setFormatter(formatter)
    info_handler.addFilter(LevelFilter(logging.INFO))
    
    warning_handler = logging.FileHandler('logs/warning.log', mode='w')
    warning_handler.setFormatter(formatter)
    warning_handler.addFilter(LevelFilter(logging.WARNING))
    
    error_handler = logging.FileHandler('logs/error.log', mode='w')
    error_handler.setFormatter(formatter)
    error_handler.addFilter(LevelFilter(logging.ERROR))
    
    critical_handler = logging.FileHandler('logs/critical.log', mode='w')
    critical_handler.setFormatter(formatter)
    critical_handler.addFilter(LevelFilter(logging.CRITICAL))
    
    # StreamHandler para consola - solo mostrar lo importante (WARNING+)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.WARNING)
    
    logger.addHandler(debug_handler)
    logger.addHandler(info_handler)
    logger.addHandler(warning_handler)
    logger.addHandler(error_handler)
    logger.addHandler(critical_handler)
    logger.addHandler(stream_handler)
    
    app = create_app(DevConfig)
    app.run(
        host=DevConfig.HOST,
        port=DevConfig.PORT,
        debug=DevConfig.DEBUG
    )
