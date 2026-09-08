"""Probe script for GET /api/integration/control-novedades.

Chosen invoices (read from app/data/control_errores.json via
app/utils/errores_storage.py logic on 2026-09-08):
  - FEV440927 (creado_en 2026-08-30T18:46:08, estado S) — most recent real invoice.
  - FEV441259 (creado_en 2026-08-26T18:12:01, estado S) — second most recent real.
  - FEV441242 (creado_en 2026-08-26T18:11:54, estado S) — third most recent real.

Why these: September (2026-09) holds 97 records but ALL are synthetic test
keys FAC-001 / FAC-002 (estado S), with zero real `factura` values. Per spec
fallback ("si no hay usa las mas recientes con factura valida"), the three
most recent valid FEV* invoices were picked, skipping junk key FEVASDAFAS.

Usage:
  set CONTROL_BEARER=<token>  (never hardcode it here)
  python scripts/probar_consulta_septiembre.py [--dry-run] [--help]
"""

import argparse
import json
import logging
import os
import sys
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

DEFAULT_BASE = "http://127.0.0.1:5000"
ENDPOINT = "/api/integration/control-novedades"
DEFAULT_FACTURAS = ["FEV440927", "FEV441259", "FEV441242"]
MISSING_FACTURA = "FEV000000-NOEXISTE"


def get_config():
    """Read config from env; fail clearly when bearer token is missing."""
    base = os.environ.get("CONTROL_API_BASE", DEFAULT_BASE).rstrip("/")
    token = os.environ.get("CONTROL_BEARER", "")
    if not token:
        logger.error("Missing CONTROL_BEARER env var (plain bearer token).")
        raise SystemExit(2)
    return base, token


def build_url(base, facturas, comma=False):
    """Build query URL using repeated or comma-separated factura params."""
    if comma:
        query = urllib.parse.urlencode({"factura": ",".join(facturas)})
    else:
        query = urllib.parse.urlencode([("factura", f) for f in facturas])
    return base + ENDPOINT + ("?" + query if query else "")


def do_get(url, token, timeout=15):
    """Perform authenticated GET; return (http_status, envelope dict)."""
    req = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + token}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except Exception:
            return exc.code, {"status": "error", "data": {}, "errors": [str(exc)]}
    except Exception as exc:
        logger.exception("Request failed")
        return 0, {"status": "error", "data": {}, "errors": [str(exc)]}


def log_result(label, url, status, envelope):
    """Log HTTP status plus solicitadas/no_encontradas and per-invoice counts."""
    data = envelope.get("data", {}) if isinstance(envelope, dict) else {}
    solicitadas = data.get("facturas_solicitadas", [])
    no_encontradas = data.get("no_encontradas", [])
    por_factura = data.get("por_factura", {})
    counts = {k: len(v) for k, v in por_factura.items()} if por_factura else {}
    logger.info("%s -> %s", label, url)
    logger.info("http_status=%s envelope_status=%s", status, envelope.get("status"))
    logger.info("facturas_solicitadas=%s", solicitadas)
    logger.info("no_encontradas=%s", no_encontradas)
    logger.info("conteo_por_factura=%s errors=%s", counts, envelope.get("errors"))


def run_case(base, token, label, facturas, comma=False, dry_run=False):
    """Run one query case; dry-run only prints the URL without network."""
    url = build_url(base, facturas, comma=comma)
    if dry_run:
        logger.info("[dry-run] %s -> %s", label, url)
        return 0, {"status": "success", "data": {}, "errors": []}
    status, envelope = do_get(url, token)
    log_result(label, url, status, envelope)
    return status, envelope


def parse_args(argv):
    """Parse CLI flags for the probe script."""
    parser = argparse.ArgumentParser(
        description="Probe GET /api/integration/control-novedades."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Build URLs without network calls.")
    parser.add_argument("--base", default=None,
                        help="Override CONTROL_API_BASE.")
    return parser.parse_args(argv)


def main(argv=None):
    """Run single, repeated-param, comma-separated, and missing cases."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv or sys.argv[1:])
    if args.dry_run:
        base = (args.base or os.environ.get("CONTROL_API_BASE",
                                            DEFAULT_BASE)).rstrip("/")
        logger.info("dry-run base=%s (no token required)", base)
    else:
        base, token = get_config()
        if args.base:
            base = args.base.rstrip("/")
    token = "" if args.dry_run else token
    run_case(base, token, "single", DEFAULT_FACTURAS[:1],
             dry_run=args.dry_run)
    run_case(base, token, "repeated-params", DEFAULT_FACTURAS[:2],
             dry_run=args.dry_run)
    run_case(base, token, "comma-separated", DEFAULT_FACTURAS[:2], comma=True,
             dry_run=args.dry_run)
    run_case(base, token, "missing", [MISSING_FACTURA],
             dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
