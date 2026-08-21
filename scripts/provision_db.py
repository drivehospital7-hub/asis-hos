"""Provisiona la base de datos de producción y el `.env` local.

Copia el esquema completo (sin datos) de `asis_hos` (SOLO lectura) hacia
`control_system_prod` en el MISMO servicio PostgreSQL (puerto 5433), deja
TODAS las tablas vacías y genera el `.env` no versionado que apunta a la
nueva base. El script es idempotente: cada ejecución produce el mismo estado
final y verifica el resultado embebido (esquema, tablas vacías, integridad de
FKs y fuente intacta).

Uso:
    python scripts/provision_db.py

Requiere credencial `postgres/postgres` (patrón .env.example) y los binarios
pg_dump/psql de PostgreSQL 18 (PATH o ruta por defecto de Windows).
"""

import logging
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg2

logger = logging.getLogger("provision_db")

# ── Constantes del pipeline ────────────────────────────────────────────────
DB_HOST = "localhost"
DB_PORT = 5433
DB_USER = "postgres"
DB_PASSWORD = "postgres"
SOURCE_DB = "asis_hos"
DEST_DB = "control_system_prod"
TEST_DB = "asis_hos_test"
POSTGRES_BIN_DEFAULT = Path(r"C:\Program Files\PostgreSQL\18\bin")

# Tablas del esquema — 14 tablas en total, verificado contra la fuente.
# Alcance: SOLO esquema, sin datos (ni semilla ni facturación).
ALL_TABLES = (
    "users", "reglas", "catalogos", "condiciones",
    "procedimiento", "notas_tecnicas", "nota_hoja", "eps_nota",
    "eps_contratado", "evidencias", "user_areas", "resultados_auditoria",
    "excepciones", "api_tokens",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
ENV_TEMPLATE = PROJECT_ROOT / ".env.example"

# Claves que el script fija en .env; el resto de la plantilla se conserva.
# SECRET_KEY se completa con secrets.token_hex(32) al generar el archivo.
ENV_OVERRIDES = {
    "SECRET_KEY": None,
    "DB_HOST": DB_HOST,
    "DB_PORT": str(DB_PORT),
    "DB_NAME": DEST_DB,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}


def _base_env() -> dict:
    """Entorno para subprocess con la credencial y encoding forzado a UTF-8."""
    env = dict(os.environ)
    env["PGPASSWORD"] = DB_PASSWORD
    env["PGCLIENTENCODING"] = "UTF8"
    return env


def _pg_bin(name: str) -> str:
    """Resuelve la ruta de un binario de PostgreSQL (PATH o ruta por defecto)."""
    found = shutil.which(name)
    if found:
        return found
    default = POSTGRES_BIN_DEFAULT / (name + ".exe")
    if default.exists():
        return str(default)
    raise RuntimeError(
        f"No se encontró {name} en el PATH ni en {POSTGRES_BIN_DEFAULT}"
    )


def _connect(dbname: str):
    """Crea una conexión psycopg2 al servicio local (5433)."""
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=dbname,
        user=DB_USER, password=DB_PASSWORD,
    )


def _pg_pipe(dump_args: list, load_args: list) -> None:
    """Ejecuta pg_dump y vuelca su salida en psql vía pipe (bytes UTF-8)."""
    env = _base_env()
    dump = subprocess.run(
        [_pg_bin("pg_dump")] + dump_args, capture_output=True, env=env
    )
    if dump.returncode != 0:
        raise RuntimeError(
            "pg_dump falló: " + dump.stderr.decode(errors="replace").strip()
        )
    load = subprocess.run(
        [_pg_bin("psql")] + load_args, input=dump.stdout,
        capture_output=True, env=env,
    )
    if load.returncode != 0:
        raise RuntimeError(
            "psql falló: " + load.stderr.decode(errors="replace").strip()
        )


def _connect_args() -> list:
    """Argumentos comunes de conexión para psql/pg_dump."""
    return ["-h", DB_HOST, "-p", str(DB_PORT), "-U", DB_USER]


# ── Pipeline (R1–R5) ───────────────────────────────────────────────────────
def ensure_database() -> None:
    """Crea la base destino si no existe; si existe, reporta el estado (R1)."""
    conn = _connect("postgres")
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DEST_DB,))
            if cur.fetchone():
                logger.info("La base %s ya existe — se continúa (idempotente)", DEST_DB)
                return
            cur.execute(
                f"CREATE DATABASE {DEST_DB} OWNER {DB_USER}"
            )
            logger.info("Base %s creada con owner %s", DEST_DB, DB_USER)
    finally:
        conn.close()


def copy_schema() -> None:
    """Copia el esquema de la fuente al destino (R2), sin tocar la fuente.

    Reinicia el esquema public del destino primero para que la re-ejecución
    produzca siempre el mismo estado final (idempotencia real).
    """
    psql = _pg_bin("psql")
    reset = subprocess.run(
        [psql] + _connect_args() + ["-d", DEST_DB, "-q", "-c",
                                    "DROP SCHEMA IF EXISTS public CASCADE;"
                                    " CREATE SCHEMA public;"],
        capture_output=True, env=_base_env(),
    )
    if reset.returncode != 0:
        raise RuntimeError(
            "No se pudo reiniciar el esquema public de " + DEST_DB + ": "
            + reset.stderr.decode(errors="replace").strip()
        )
    _pg_pipe(
        _connect_args() + ["-d", SOURCE_DB,
                           "--schema-only", "--no-owner", "--no-privileges"],
        _connect_args() + ["-d", DEST_DB, "-v", "ON_ERROR_STOP=1", "-q"],
    )
    logger.info("Esquema copiado de %s a %s", SOURCE_DB, DEST_DB)


def write_env() -> None:
    """Genera .env no versionado desde .env.example (R5).

    No sobrescribe un .env existente para proteger la SECRET_KEY actual.
    """
    if ENV_PATH.exists():
        logger.info(".env ya existe — se conserva (no se sobrescribe)")
        return
    if not ENV_TEMPLATE.exists():
        raise RuntimeError(f"No existe la plantilla {ENV_TEMPLATE}")
    secret = secrets.token_hex(32)
    lines = ENV_TEMPLATE.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        stripped = line.lstrip()
        key = stripped.split("=", 1)[0].strip() if stripped and not stripped.startswith("#") else None
        if key in ENV_OVERRIDES:
            value = ENV_OVERRIDES[key] if ENV_OVERRIDES[key] is not None else secret
            out.append(f"{key}={value}")
        else:
            out.append(line)
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    logger.info(".env generado en %s", ENV_PATH)


# ── Verificación (R4) ──────────────────────────────────────────────────────
def _table_count(conn, table: str) -> int:
    """Cuenta filas de una tabla."""
    with conn.cursor() as cur:
        cur.execute(f'SELECT count(*) FROM "{table}"')
        return cur.fetchone()[0]


def _object_counts(conn) -> tuple:
    """Cuenta tablas, secuencias e índices del esquema public."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
        tables = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM pg_sequences WHERE schemaname='public'")
        sequences = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM pg_indexes WHERE schemaname='public'")
        indexes = cur.fetchone()[0]
    return tables, sequences, indexes


def _orphan_counts(conn) -> dict:
    """Cuenta filas huérfanas por constraint FK (FKs de una sola columna)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT con.conname, rel.relname, parent.relname,"
            "       att.attname, patt.attname"
            " FROM pg_constraint con"
            " JOIN pg_class rel ON rel.oid = con.conrelid"
            " JOIN pg_class parent ON parent.oid = con.confrelid"
            " JOIN pg_attribute att ON att.attrelid = con.conrelid"
            "                        AND att.attnum = con.conkey[1]"
            " JOIN pg_attribute patt ON patt.attrelid = con.confrelid"
            "                         AND patt.attnum = con.confkey[1]"
            " WHERE con.contype = 'f'"
        )
        fks = cur.fetchall()
    orphans = {}
    for conname, child, parent, child_col, parent_col in fks:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT count(*) FROM "{child}" c'
                f' LEFT JOIN "{parent}" p ON c."{child_col}" = p."{parent_col}"'
                f' WHERE c."{child_col}" IS NOT NULL AND p."{parent_col}" IS NULL'
            )
            orphans[conname] = cur.fetchone()[0]
    return orphans


def _capture_all_counts() -> dict:
    """Rowcounts de todas las tablas de la fuente y su DB de prueba."""
    counts = {}
    for dbname in (SOURCE_DB, TEST_DB):
        conn = _connect(dbname)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tablename FROM pg_tables"
                    " WHERE schemaname='public'"
                )
                tables = [row[0] for row in cur.fetchall()]
            counts[dbname] = {t: _table_count(conn, t) for t in tables}
        finally:
            conn.close()
    return counts


def verify(baseline: dict) -> list:
    """Ejecuta las verificaciones y devuelve [(check, ok, detalle), ...].

    - Esquema del destino igual a la fuente (tablas/secuencias/índices).
    - Todas las tablas del destino con 0 filas (solo esquema).
    - 0 filas huérfanas en todas las FKs del destino.
    - Fuente y su DB de prueba intactas (baseline vs estado posterior).
    """
    results = []
    source = _connect(SOURCE_DB)
    dest = _connect(DEST_DB)
    try:
        src_counts = _object_counts(source)
        dst_counts = _object_counts(dest)
        for name, value, expected in (
            ("tablas", dst_counts[0], src_counts[0]),
            ("secuencias", dst_counts[1], src_counts[1]),
            ("índices", dst_counts[2], src_counts[2]),
        ):
            results.append((f"esquema: {name}", value == expected,
                            f"destino {value} == fuente {expected}"))
        for table in ALL_TABLES:
            dst_count = _table_count(dest, table)
            results.append((f"vacía: {table}", dst_count == 0,
                            f"{dst_count} filas"))
        for conname, count in _orphan_counts(dest).items():
            results.append((f"FK sin huérfanos: {conname}", count == 0,
                            f"{count} huérfanas"))
        after = _capture_all_counts()
        for dbname in (SOURCE_DB, TEST_DB):
            ok = after[dbname] == baseline[dbname]
            results.append((f"fuente intacta: {dbname}", ok,
                            "rowcounts idénticos antes/después"))
    finally:
        source.close()
        dest.close()
    return results


def main() -> int:
    """Orquesta R1→R5 y la verificación; exit 0 si todo OK, 1 si falla."""
    # Consolas Windows: emitir UTF-8 para no corromper los acentos del log
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # Python < 3.7 o stream sin reconfigure: se deja el default
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Provisioning de %s (puerto %s) iniciado", DEST_DB, DB_PORT)
    try:
        baseline = _capture_all_counts()
        logger.info("Baseline de fuente capturado (%s y %s)", SOURCE_DB, TEST_DB)
        ensure_database()
        copy_schema()
        write_env()
        results = verify(baseline)
        failed = [name for name, ok, _ in results if not ok]
        for name, ok, detail in results:
            state = "OK" if ok else "FAIL"
            logger.info("Verificación [%s] %s: %s", state, name, detail)
        if failed:
            logger.error("Verificación fallida: %s", ", ".join(failed))
            return 1
        logger.info("Provisioning completado: %s checks OK", len(results))
        logger.info("Destino: %s (5433) — .env: %s", DEST_DB, ENV_PATH)
        return 0
    except Exception as exc:  # noqa: BLE001 — reporte final y exit code
        logger.exception("Provisioning falló: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
