import sys
sys.path.insert(0, r"D:\CODE\control_system_unificado")

from dotenv import load_dotenv
load_dotenv()

from app.utils.db_config import get_database_config
import psycopg2

config = get_database_config()
conn = psycopg2.connect(**config.psycopg2_dsn)
cur = conn.cursor()

# CUPS 993505
cur.execute("SELECT id, cups, procedimiento FROM procedimiento WHERE cups = %s", ("993505",))
print("=== Procedimiento 993505 ===")
for r in cur.fetchall():
    print(f"  id={r[0]}, cups={r[1]}, proc={r[2]}")

# Buscar por nombre exacto Vacunacion contra Rabia
cur.execute("SELECT id, cups, procedimiento FROM procedimiento WHERE procedimiento ILIKE '%rabia%'")
print("\n=== Procedimientos con Rabia ===")
for r in cur.fetchall():
    print(f"  id={r[0]}, cups={r[1]}, proc={r[2]}")

cur.execute("SELECT id, cups, procedimiento FROM procedimiento WHERE procedimiento ILIKE '%vacunacion%' ORDER BY cups")
print("\n=== Procedimientos con Vacunacion ===")
for r in cur.fetchall():
    print(f"  id={r[0]}, cups={r[1]}, proc={r[2]}")

# NotaHoja vinculadas a 993505
cur.execute("""
    SELECT nh.id, nh.nota, nh.valor_unitario, nh.cod_entidad
    FROM nota_hoja nh
    JOIN procedimiento p ON p.id = nh.id_procedimiento
    WHERE p.cups = %s
""", ("993505",))
print("\n=== NotaHoja vinculadas ===")
rows = cur.fetchall()
print(f"  Total: {len(rows)}")
for r in rows:
    print(f"  id={r[0]}, nota={r[1]}, valor={r[2]}, entidad={r[3]}")

# EpsNota via NotaHoja + 993505
cur.execute("""
    SELECT en.id, en.id_nota_hoja, en.id_eps, en.cod_contrato, en.anio, en.mes
    FROM eps_nota en
    JOIN nota_hoja nh ON nh.id = en.id_nota_hoja
    JOIN procedimiento p ON p.id = nh.id_procedimiento
    WHERE p.cups = %s
""", ("993505",))
print("\n=== EpsNota vinculadas ===")
rows = cur.fetchall()
print(f"  Total: {len(rows)}")
for r in rows:
    print(f"  en.id={r[0]}, nh_id={r[1]}, eps_id={r[2]}, contrato={r[3]}, anio={r[4]}, mes={r[5]}")

# EPS ESS062
cur.execute("SELECT id, nit, nombre, cod_contrato FROM eps_contratado WHERE cod_contrato LIKE %s", ("%ESS062%",))
print("\n=== EPS ESS062 ===")
for r in cur.fetchall():
    print(f"  id={r[0]}, nit={r[1]}, nombre={r[2]}, contrato={r[3]}")

# NotaHoja directo ESS062 + 993505
cur.execute("""
    SELECT id, nota, id_procedimiento, cod_entidad
    FROM nota_hoja
    WHERE cod_entidad LIKE '%ESS062%'
      AND id_procedimiento IN (SELECT id FROM procedimiento WHERE cups = '993505')
""")
print("\n=== NotaHoja ESS062 + 993505 directo ===")
rows = cur.fetchall()
print(f"  Total: {len(rows)}")
for r in rows:
    print(f"  id={r[0]}, nota={r[1]}, proc_id={r[2]}, entidad={r[3]}")

# Tablas con resolucion
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%resol%' ORDER BY table_name")
print("\n=== Tablas resolucion ===")
for r in cur.fetchall():
    print(f"  {r[0]}")

cur.close()
conn.close()
print("\nDone.")
