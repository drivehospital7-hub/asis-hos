"""Script para crear la base de datos de procedimientos.

Uso:
    python data/create_db.py
"""

import sqlite3
import csv
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).parent / "db_contratos_limpio.csv"
DB_PATH = Path(__file__).parent / "procedimientos.db"


def create_database():
    """Crea la DB SQLite e importa el CSV usando el módulo csv (maneja comas dentro de campos)."""
    
    # Delete existing DB if exists
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table (solo id es PK, codigo_cups se puede repetir entre EPS)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS procedimientos (
            id INTEGER PRIMARY KEY,
            eps TEXT NOT NULL,
            codigo_cups TEXT NOT NULL,
            descripcion TEXT,
            tarifa REAL
        )
    """)
    
    # Create index for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_lookup 
        ON procedimientos(eps, codigo_cups)
    """)
    
    # Read and import CSV using csv module (handles quoted fields properly)
    imported = 0
    skipped = 0
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            row_id = row.get('id', '').strip()
            eps = row.get('eps', '').strip()
            codigo = row.get('codigo_cups', '').strip()
            descripcion = row.get('descripcion', '').strip()
            tarifa_str = row.get('tarifa', '').strip()
            
            if not eps or not codigo:
                skipped += 1
                continue
            
            # Convert tariff to float (empty = None)
            tarifa = None
            if tarifa_str:
                try:
                    tarifa = float(tarifa_str.replace(',', '.'))
                except ValueError:
                    logger.warning("Tarifa inválida '%s' para %s", tarifa_str, codigo)
            
            try:
                cursor.execute("""
                    INSERT INTO procedimientos 
                    (id, eps, codigo_cups, descripcion, tarifa)
                    VALUES (?, ?, ?, ?, ?)
                """, (row_id, eps, codigo, descripcion, tarifa))
                imported += 1
            except sqlite3.IntegrityError:
                skipped += 1
    
    conn.commit()
    
    # Show stats
    cursor.execute("SELECT COUNT(*), COUNT(tarifa), COUNT(DISTINCT eps) FROM procedimientos")
    total, con_tarifa, eps_unicas = cursor.fetchone()
    
    logger.info("DB creada: %s registros, %s con tarifa, %s EPS únicas", 
              total, con_tarifa, eps_unicas)
    
    # Show sample
    cursor.execute("SELECT eps, codigo_cups, descripcion, tarifa FROM procedimientos LIMIT 10")
    print("\n--- Muestra de datos ---")
    for row in cursor.fetchall():
        desc = row[2][:50] if row[2] else "(sin descripción)"
        print(f"  {row[0]} | {row[1]} | {desc}... | {row[3]}")
    
    conn.close()
    print(f"\n✅ Base de datos creada: {DB_PATH}")
    print(f"   Total: {imported} importados, {skipped} duplicados omitidos")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_database()