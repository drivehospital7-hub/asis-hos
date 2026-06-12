import sys
sys.path.insert(0, r"D:\CODE\control_system_unificado")

from dotenv import load_dotenv
load_dotenv()

from app.utils.db_config import get_database_config
import psycopg2

config = get_database_config()
conn = psycopg2.connect(**config.psycopg2_dsn)
cur = conn.cursor()

# Columns in nota_hoja
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'nota_hoja' ORDER BY ordinal_position")
print("=== Columnas nota_hoja ===")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

print()

# Columns in procedimiento
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'procedimiento' ORDER BY ordinal_position")
print("=== Columnas procedimiento ===")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

print()

# Columns in eps_nota
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'eps_nota' ORDER BY ordinal_position")
print("=== Columnas eps_nota ===")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

print()

# How is nota_hoja linked to procedimiento? Look at foreign keys
cur.execute("""
    SELECT
        tc.constraint_name,
        tc.table_name AS source_table,
        kcu.column_name AS source_column,
        ccu.table_name AS target_table,
        ccu.column_name AS target_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND (tc.table_name IN ('nota_hoja', 'procedimiento', 'eps_nota', 'eps_contratado', 'notas_tecnicas'))
    ORDER BY tc.table_name, tc.constraint_name
""")
print("=== Foreign Keys (relevantes) ===")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}.{r[2]} -> {r[3]}.{r[4]}")

cur.close()
conn.close()
print("\nDone.")
