"""Script para importar CSV desde data/import/."""

import sys
from pathlib import Path
import csv

from dotenv import load_dotenv
import psycopg2

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.db_config import get_database_config


def import_eps_nota(config):
    """Importa eps_nota desde CSV."""
    csv_path = Path(__file__).parent / "data" / "import" / "eps_nota.csv"
    
    if not csv_path.exists():
        print(f"❌ No existe: {csv_path}")
        return
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        imported = 0
        for row in reader:
            conn = psycopg2.connect(**config.psycopg2_dsn)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO eps_nota (id_eps_contratado, id_nota_hoja)
                    VALUES (%s, %s)
                """, (int(row['id_eps_contratado']), int(row['id_nota_hoja'])))
                conn.commit()
                imported += 1
            except psycopg2.Error as e:
                print(f"❌ Error: {row} - {e.pgerror.splitlines()[0]}")
            finally:
                cursor.close()
                conn.close()
    
    print(f"✅ eps_nota importadas: {imported}")
    
    conn = psycopg2.connect(**config.psycopg2_dsn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM eps_nota")
    print(f'Total en DB: {cur.fetchone()[0]}')
    cur.close()
    conn.close()


if __name__ == "__main__":
    config = get_database_config()
    import_eps_nota(config)
