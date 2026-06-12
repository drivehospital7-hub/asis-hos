import sys
sys.path.insert(0, r"D:\CODE\control_system_unificado")

from dotenv import load_dotenv
load_dotenv()

from app.utils.db_config import get_database_config
import psycopg2

config = get_database_config()
conn = psycopg2.connect(**config.psycopg2_dsn)
cur = conn.cursor()

# 1. Procedimientos con RABIA
cur.execute("SELECT id, cups, procedimiento FROM procedimiento WHERE procedimiento ILIKE '%rabia%'")
print("=== VACUNACION CONTRA RABIA ===")
rabia_ids = []
for r in cur.fetchall():
    print(f"  id={r[0]}, cups={r[1]}, proc={r[2]}")
    rabia_ids.append(r[0])

if not rabia_ids:
    print("No hay procedimientos con RABIA. Fin.")
    cur.close()
    conn.close()
    sys.exit(0)

rabia_tup = tuple(rabia_ids)

# 2. Notas_tecnicas que referencian esos procedimientos
cur.execute("""
    SELECT nt.id, nt.id_nota_hoja, nt.id_procedimiento
    FROM notas_tecnicas nt
    WHERE nt.id_procedimiento IN %s
    ORDER BY nt.id
""", (rabia_tup,))
print(f"\n=== Notas_tecnicas vinculadas a Rabia ===")
rows = cur.fetchall()
print(f"  Registros: {len(rows)}")
na_notas_ids = set()
for r in rows:
    na_notas_ids.add(r[1])
    print(f"  nt.id={r[0]}, nh_id={r[1]}, proc_id={r[2]}")

# 3. NotaHoja vinculadas
print(f"\n=== NotaHoja vinculadas ({len(na_notas_ids)} ids) ===")
if na_notas_ids:
    cur.execute("SELECT id, nota FROM nota_hoja WHERE id IN %s ORDER BY id", (tuple(na_notas_ids),))
    for r in cur.fetchall():
        print(f"  id={r[0]}, nota={r[1]}")

# 4. EPS de esas NotaHoja via eps_nota
print("\n=== EpsNota por esas NotaHoja ===")
if na_notas_ids:
    cur.execute("""
        SELECT en.id, en.id_nota_hoja, en.id_eps_contratado, ec.cod_contrato, ec.nombre
        FROM eps_nota en
        LEFT JOIN eps_contratado ec ON ec.id = en.id_eps_contratado
        WHERE en.id_nota_hoja IN %s
        ORDER BY en.id
    """, (tuple(na_notas_ids),))
    for r in cur.fetchall():
        print(f"  en.id={r[0]}, nh_id={r[1]}, eps_contratado_id={r[2]}, contrato={r[3]}, nombre={r[4]}")

# 5. ESS062 especificamente
print("\n=== ESS062 en eps_contratado ===")
cur.execute("SELECT id, nit, cod_contrato, nombre FROM eps_contratado WHERE cod_contrato LIKE '%ESS062%'")
for r in cur.fetchall():
    print(f"  id={r[0]}, nit={r[1]}, contrato={r[2]}, nombre={r[3]}")

# 6. Rabia + ESS062 - existe la combinacion?
print("\n=== RABIA + ESS062: existe? ===")
if na_notas_ids:
    cur.execute("""
        SELECT nh.id, nh.nota, ec.cod_contrato, ec.nombre
        FROM eps_nota en
        JOIN nota_hoja nh ON nh.id = en.id_nota_hoja
        JOIN eps_contratado ec ON ec.id = en.id_eps_contratado
        WHERE en.id_nota_hoja IN %s
          AND ec.cod_contrato LIKE '%ESS062%'
    """, (tuple(na_notas_ids),))
    rows2 = cur.fetchall()
    print(f"  Registros: {len(rows2)}")
    for r in rows2:
        print(f"  nh.id={r[0]}, nota={r[1]}, contrato={r[2]}, nombre={r[3]}")
    if not rows2:
        print("  -> NO existen NotaHoja con ESS062 y RABIA")

# 7. Resolucion interna - a que se refiere? tablas con resol
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%resol%' ORDER BY table_name")
print("\n=== Tablas con 'resol' ===")
for r in cur.fetchall():
    print(f"  {r[0]}")

# 8. not what the user means by "resolucion interna"? Buscar en el codigo
print("\n=== NOTA_hoja con 'resol' ===")
cur.execute("SELECT id, nota FROM nota_hoja WHERE nota ILIKE '%resol%' ORDER BY id")
for r in cur.fetchall():
    print(f"  id={r[0]}, nota={r[1]}")

print("\n=== NOTA_hoja con ASMET ===")
cur.execute("SELECT id, nota FROM nota_hoja WHERE nota ILIKE '%asmet%'")
for r in cur.fetchall():
    print(f"  id={r[0]}, nota={r[1]}")

# 9. Una NotaHoja que tenga ambos: "resolucion" y "asmet"?
print("\n=== Buscando relacion Resolucion + EPS ===")
cur.execute("""
    SELECT nh.id, nh.nota, ec.cod_contrato, ec.nombre
    FROM eps_nota en
    JOIN nota_hoja nh ON nh.id = en.id_nota_hoja
    JOIN eps_contratado ec ON ec.id = en.id_eps_contratado
    WHERE ec.cod_contrato LIKE '%ESS062%'
    ORDER BY nh.id
""")
rows3 = cur.fetchall()
print(f"  Total EPS ESS062 con nota: {len(rows3)}")
for r in rows3[:10]:
    print(f"  nh.id={r[0]}, nota={r[1]}, contrato={r[2]}, nombre={r[3]}")

cur.close()
conn.close()
print("\nDone.")
