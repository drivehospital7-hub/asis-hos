"""Eliminacion segura de registros V-pattern del catalogo.

Orden: dependencias -> principales, respetando FK constraints.
"""

import sys
sys.path.insert(0, r"D:\CODE\control_system_unificado")

from dotenv import load_dotenv
load_dotenv()

from app.utils.db_config import get_database_config
import psycopg2

config = get_database_config()
conn = psycopg2.connect(**config.psycopg2_dsn)
conn.autocommit = False
cur = conn.cursor()

try:
    # ─── 1. Contar ────────────────────────────────────────────────────
    print("=== CONTEO PREVIO ===")

    cur.execute("""
        SELECT COUNT(*) FROM notas_tecnicas nt
        JOIN nota_hoja nh ON nh.id = nt.id_nota_hoja
        WHERE nh.nota LIKE 'NOTA V%'
    """)
    nt_v = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM eps_nota en
        JOIN nota_hoja nh ON nh.id = en.id_nota_hoja
        WHERE nh.nota LIKE 'NOTA V%'
    """)
    en_v = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM nota_hoja WHERE nota LIKE 'NOTA V%'")
    nh_v = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM eps_contratado WHERE cod_contrato LIKE 'V%_EPS'")
    eps_v = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM procedimiento WHERE procedimiento LIKE 'PROC V%'")
    proc_v = cur.fetchone()[0]

    print(f"  notas_tecnicas (linked to NOTA V*): {nt_v}")
    print(f"  eps_nota (linked to NOTA V*):        {en_v}")
    print(f"  nota_hoja (NOTA V*):                 {nh_v}")
    print(f"  eps_contratado (V*_EPS):             {eps_v}")
    print(f"  procedimiento (PROC V*):             {proc_v}")
    print(f"  TOTAL a eliminar:                     {nt_v + en_v + nh_v + eps_v + proc_v}")

    if nt_v + en_v + nh_v + eps_v + proc_v == 0:
        print("\nNada para eliminar.")
        sys.exit(0)

    # ─── 2. Mostrar muestra ───────────────────────────────────────────
    print("\n=== MUESTRA (primeros 3 de cada tipo) ===")
    cur.execute("SELECT nota FROM nota_hoja WHERE nota LIKE 'NOTA V%' ORDER BY id LIMIT 3")
    for r in cur.fetchall():
        print(f"  nota_hoja: {r[0]}")

    cur.execute("SELECT cod_contrato, eps FROM eps_contratado WHERE cod_contrato LIKE 'V%_EPS' ORDER BY id LIMIT 3")
    for r in cur.fetchall():
        print(f"  eps_contratado: {r[0]} -> {r[1]}")

    cur.execute("SELECT cups, procedimiento FROM procedimiento WHERE procedimiento LIKE 'PROC V%' ORDER BY id LIMIT 3")
    for r in cur.fetchall():
        print(f"  procedimiento: cups={r[0]} | {r[1]}")

    # ─── 3. Eliminar en orden ─────────────────────────────────────────
    print("\n=== ELIMINANDO ===")

    # 3a: notas_tecnicas linked to V-pattern NotaHoja
    cur.execute("""
        DELETE FROM notas_tecnicas
        WHERE id_nota_hoja IN (
            SELECT id FROM nota_hoja WHERE nota LIKE 'NOTA V%'
        )
    """)
    print(f"  notas_tecnicas (via NH): {cur.rowcount}")

    # 3b: notas_tecnicas linked to PROC V procedimientos (FK cruzadas)
    cur.execute("""
        DELETE FROM notas_tecnicas
        WHERE id_procedimiento IN (
            SELECT id FROM procedimiento WHERE procedimiento LIKE 'PROC V%'
        )
    """)
    print(f"  notas_tecnicas (via PROC): {cur.rowcount}")

    # 3c: eps_nota linked to V-pattern
    cur.execute("""
        DELETE FROM eps_nota
        WHERE id_nota_hoja IN (
            SELECT id FROM nota_hoja WHERE nota LIKE 'NOTA V%'
        )
    """)
    print(f"  eps_nota: {cur.rowcount}")

    # 3d: procedimiento PROC V*
    cur.execute("DELETE FROM procedimiento WHERE procedimiento LIKE 'PROC V%'")
    print(f"  procedimiento: {cur.rowcount}")

    # 3e: nota_hoja NOTA V*
    cur.execute("DELETE FROM nota_hoja WHERE nota LIKE 'NOTA V%'")
    print(f"  nota_hoja: {cur.rowcount}")

    # 3f: eps_contratado V*_EPS
    cur.execute("DELETE FROM eps_contratado WHERE cod_contrato LIKE 'V%_EPS'")
    print(f"  eps_contratado: {cur.rowcount}")

    conn.commit()
    print("\n=== VERIFICACION ===")
    cur.execute("SELECT COUNT(*) FROM nota_hoja WHERE nota LIKE 'NOTA V%'")
    print(f"  nota_hoja V* restantes: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM eps_contratado WHERE cod_contrato LIKE 'V%_EPS'")
    print(f"  eps_contratado V* restantes: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM procedimiento WHERE procedimiento LIKE 'PROC V%'")
    print(f"  procedimiento PROC V* restantes: {cur.fetchone()[0]}")

    # Totales finales
    cur.execute("SELECT COUNT(*) FROM nota_hoja")
    nh_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM eps_contratado")
    eps_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM procedimiento")
    proc_total = cur.fetchone()[0]

    print(f"\nTotales finales:")
    print(f"  nota_hoja: {nh_total}")
    print(f"  eps_contratado: {eps_total}")
    print(f"  procedimiento: {proc_total}")

    print("\nLimpieza completada.")

except Exception as e:
    conn.rollback()
    print(f"\nERROR: {e}")
    raise
finally:
    cur.close()
    conn.close()
