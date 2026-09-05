import sys
sys.path.insert(0, r"D:\CODE\control_system_unificado")

from dotenv import load_dotenv
load_dotenv()

from app.utils.db_config import get_database_config
import psycopg2

config = get_database_config()
conn = psycopg2.connect(**config.psycopg2_dsn)
cur = conn.cursor()

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'eps_contratado' ORDER BY ordinal_position")
print("=== Columnas eps_contratado ===")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'notas_tecnicas' ORDER BY ordinal_position")
print("\n=== Columnas notas_tecnicas ===")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'nota_hoja' ORDER BY ordinal_position")
print("\n=== Columnas nota_hoja ===")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

cur.close()
conn.close()
