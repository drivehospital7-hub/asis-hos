"""Exporta todas las notas técnicas con sus procedimientos (CUPS) a CSV."""

import csv
import os
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "dbname": os.getenv("DB_NAME", "asis_hos"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

QUERY = """
SELECT
    nt.id AS notas_tecnicas_id,
    nt.id_nota_hoja,
    nh.nota AS nombre_nota,
    p.id AS procedimiento_id,
    p.cups,
    p.procedimiento AS nombre_procedimiento,
    nt.tariff AS tarifa
FROM notas_tecnicas nt
JOIN procedimiento p ON p.id = nt.id_procedimiento
JOIN nota_hoja nh ON nh.id = nt.id_nota_hoja
ORDER BY nh.nota, p.cups;
"""

OUTPUT_FILE = f"notas_tecnicas_procedimientos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY)
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]

        if not rows:
            print("No se encontraron registros.")
            return

        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(colnames)
            writer.writerows(rows)

        print(f"Exportados {len(rows)} registros a: {OUTPUT_FILE}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
