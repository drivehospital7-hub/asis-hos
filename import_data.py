"""Script para importar notas_tecnicas."""

import sys
from pathlib import Path
import csv

from dotenv import load_dotenv
import psycopg2

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.db_config import get_database_config


def import_notas_tecnicas(config):
    """Importa notas_tecnicas desde CSV."""
    csv_path = Path(__file__).parent / "data" / "import" / "notas_tecnicas.csv"
    
    if not csv_path.exists():
        print(f"❌ No existe: {csv_path}")
        return
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        imported = 0
        for row in reader:
            id_proc = int(row['id_procedimiento'])
            id_nota = int(row['id_nota_hoja'])
            # Usar 0 como placeholder si tarifa está vacía
            tarifa = float(row['tarifa']) if row.get('tarifa', '').strip() else 0
            
            conn = psycopg2.connect(**config.psycopg2_dsn)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notas_tecnicas (id_procedimiento, id_nota_hoja, tariff)
                    VALUES (%s, %s, %s)
                """, (id_proc, id_nota, tarifa))
                conn.commit()
                imported += 1
            except psycopg2.Error as e:
                print(f"❌ Error: proc={id_proc}, nota={id_nota} - {e.pgerror.splitlines()[0]}")
            finally:
                cursor.close()
                conn.close()
    
    print(f"✅ Notas técnicas importadas: {imported}")
    
    conn = psycopg2.connect(**config.psycopg2_dsn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM notas_tecnicas")
    print(f'Total en DB: {cur.fetchone()[0]}')
    cur.close()
    conn.close()


if __name__ == "__main__":
    config = get_database_config()
    import_notas_tecnicas(config)