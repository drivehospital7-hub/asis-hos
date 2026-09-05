import sys
sys.path.insert(0, r"D:\CODE\control_system_unificado")

from dotenv import load_dotenv
load_dotenv()

from app.utils.db_config import get_database_config
import psycopg2

config = get_database_config()
conn = psycopg2.connect(**config.psycopg2_dsn)
cur = conn.cursor()

# NotaHoja id=12
cur.execute("SELECT id, nota FROM nota_hoja WHERE id = 12")
print("=== NotaHoja id=12 ===")
r = cur.fetchone()
print(f"  id={r[0]}, nota={r[1]}")

# EpsNota vinculadas
cur.execute("""
    SELECT en.id, en.id_eps_contratado, ec.cod_contrato, ec.eps, ec.regimen
    FROM eps_nota en
    JOIN eps_contratado ec ON ec.id = en.id_eps_contratado
    WHERE en.id_nota_hoja = 12
""")
print("\n=== EpsNota (EPS relacionadas) ===")
rows = cur.fetchall()
print(f"  Registros: {len(rows)}")
for r in rows:
    print(f"  en.id={r[0]}, eps_contratado.id={r[1]}, contrato={r[2]}, eps={r[3]}, regimen={r[4]}")

# Notas_tecnicas vinculadas
cur.execute("""
    SELECT nt.id, nt.id_procedimiento, nt.tariff, p.cups, p.procedimiento
    FROM notas_tecnicas nt
    JOIN procedimiento p ON p.id = nt.id_procedimiento
    WHERE nt.id_nota_hoja = 12
""")
print("\n=== Notas_tecnicas (resolucion interna) ===")
rows = cur.fetchall()
print(f"  Registros: {len(rows)}")
for r in rows:
    print(f"  nt.id={r[0]}, proc.id={r[1]}, tariff={r[2]}, cups={r[3]}, proc={r[4][:80]}")

cur.close()
conn.close()
