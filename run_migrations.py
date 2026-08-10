"""Ejecuta migraciones de base de datos PostgreSQL."""

import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Cargar variables de entorno
load_dotenv()

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.db_config import get_database_config


def run_migrations():
    """Ejecuta todos los archivos .sql en migrations/"""
    config = get_database_config()
    
    print(f"Conectando a PostgreSQL: {config.host}:{config.port}/{config.name}")
    
    conn = psycopg2.connect(**config.psycopg2_dsn)
    conn.autocommit = True
    cursor = conn.cursor()
    
    migrations_dir = Path(__file__).parent / "migrations"
    
    if not migrations_dir.exists():
        print("ERROR: No existe directorio migrations/")
        return
    
    # Buscar todos los archivos .sql ordenados
    sql_files = sorted(migrations_dir.glob("*.sql"))
    
    if not sql_files:
        print("ERROR: No hay archivos .sql en migrations/")
        return
    
    for sql_file in sql_files:
        print(f"\nEjecutando: {sql_file.name}")
        try:
            with open(sql_file, "r", encoding="utf-8") as f:
                sql_content = f.read()
            
            cursor.execute(sql_content)
            print(f"   OK: {sql_file.name} ejecutado correctamente")
            
        except psycopg2.Error as e:
            print(f"   ERROR en {sql_file.name}: {e.pgerror}")
            continue
    
    cursor.close()
    conn.close()
    
    print("\nMigraciones completadas")


if __name__ == "__main__":
    run_migrations()
