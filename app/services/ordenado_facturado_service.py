"""Servicio para cruce de Ordenado y Facturado con Ayudas Diagnósticas.

Compara dos archivos Excel usando el mismo sistema de mapeo de columnas
que el resto del sistema (exporter.py → column_indices.py).

  - File 1 (reporte): Excel estándar con columna "Número Factura" y "Procedimiento"
  - File 2 (ayudas): Excel nuevo con columna "N° Factura" y "CUPS"

Detecta registros en ayudas que NO están facturados en el reporte.
Auto-detecta la fila de encabezados si no está en la fila 1.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from app.services.transversales.column_indices import get_column_indices

logger = logging.getLogger(__name__)

# Columnas requeridas para el REPORTE (Excel estándar)
REPORTE_REQUIRED_HEADERS: dict[str, str] = {
    "numero_factura": "Número Factura",
    "codigo": "Código",
    "procedimiento": "Procedimiento",
    "identificacion": "Nº Identificación",
    "fec_factura": "Fec. Factura",
}

# Columnas requeridas para AYUDAS DIAGNÓSTICAS (obligatorias)
AYUDAS_REQUIRED_HEADERS: dict[str, str] = {
    "numero_factura": "N° Factura",
    "cups": "CUPS",
    "tipo_factura_servicio": "Tipo Factura (Servicio)",
    "identificacion": "Nº Identificación",
    "fecha_solicitud": "Fecha Solicitud",
    "entidad_administradora": "Entidad Administradora",
    "procedimiento_solicitado": "Procedimiento Solicitado",
}

# Columnas opcionales para AYUDAS (no rompen si faltan)
AYUDAS_OPTIONAL_HEADERS: dict[str, str] = {
    "paciente": "Paciente",
    "profesional_solicito": "Profesional Solicito",
}

# Máximas filas a escanear para encontrar encabezados
MAX_SCAN_ROWS = 20

# Códigos de excepción que NO se consideran no facturados
CODIGOS_EXCEPCION: set[str] = {
    # 89xxx
    "8938011",
    # 39xxx
    "39601", "396011",
    # 6xxxx
    "601T01", "601T012", "601T02", "601T02BOGOTA", "601T02BOGOTAAUX",
    "601T02FLOREN", "601T02FLORENAUX",
    "602T02", "602T021", "60200",
    # 1xxxx
    "10000", "10000AUX", "10001", "100011", "10002", "10003", "10003AUX",
    "10006", "102", "103",
    # 11xxx
    "110001", "1100010AUX", "110001AUX", "110002", "110003", "110004",
    "1100041", "110005", "110006", "110007", "11001", "110018",
    "110018AUX", "11003", "11004", "11006", "11021",
    "110212", "11022",
    # 7xxxx
    "70000", "70000AUX", "70003", "70003AUX",
    # 8xxxx
    "80000", "80000AUX", "800001AUX",
    # Sxx
    "S31301", "S31302", "S32301", "S32302", "S33301", "S33302",
}

# Códigos de parto procesados que NO se consideran no facturados
PROCESADOS_PARTO: set[str] = {
    "735301",
    "735930",
    "735950",
    "P0000450",
    "717110",
    "717111",
    "S21100",
    "90DS02",
    "933701",
    "754101",
    "750101",
    "897011",
    "897012",
    "735980",
    "721001",
    "721002",
    "732201",
    "735300",
    "S21200",
    "906916",
}

# Códigos de interconsultas procesados que NO se consideran no facturados
PROCESADOS_INTERCONSULTAS: set[str] = {
    "890410",
    "890402",
    "890404",
    "890403",
    "890408",
    "890411",
    "890413",
    "890412",
    "890409",
    "37602",
    "39140",
    "890405",
    "890432",
    "890401",
    "890406",
    "36101",
    "37701",
    "890610",
}

# Códigos de otros procesados que NO se consideran no facturados
PROCESADOS_OTROS: set[str] = {
    "861801",
}

# Códigos que también se matchean por número de documento (como CAP)
CODIGOS_MATCH_POR_DOCUMENTO: set[str] = {"890405", "861801"}

# Columnas requeridas para NOTAS ENFERMERÍA (opcional)
NOTAS_REQUIRED_HEADERS: dict[str, str] = {
    "numero_factura": "N° Factura",
    "nota_enfermeria": "Nota Enfermeria",
}

NOTAS_OPTIONAL_HEADERS: dict[str, str] = {
    "profesional_registra": "Profesional Registra",
    "entidad_administradora": "Entidad Administradora",
    "identificacion": "Nº Identificación",
    "fecha_nota": "Fecha Nota",
}

EMSSANAR_ENTIDAD = "{ESS118} - EMSSANAR ENTIDAD PROMOTORA DE SALUD S.A.S."

# Si factura empieza con este prefijo, los códigos normales se matchean por identificación
CAP_PREFIX = "CAP"


def _detectar_fila_headers(
    rows: list[list[Any]],
    required_headers: dict[str, str],
) -> int | None:
    """Busca la primera fila que contenga TODOS los headers requeridos.

    Escanea las primeras MAX_SCAN_ROWS filas buscando una que tenga
    coincidencia exacta de todos los nombres de columna requeridos.

    Returns:
        Índice 1-based de la fila de headers, o None si no encuentra.
    """
    nombres_requeridos = set(required_headers.values())

    for row_idx in range(1, min(len(rows), MAX_SCAN_ROWS + 1)):
        valores_fila = set()
        for col in range(1, len(rows[row_idx])):
            val = rows[row_idx][col]
            if val is not None:
                valores_fila.add(str(val).strip())

        if nombres_requeridos.issubset(valores_fila):
            logger.info("Headers detectados en fila %d: %s", row_idx, valores_fila)
            return row_idx

    return None


def _leer_como_raw(path: Path) -> list[list[Any]]:
    """Lee un Excel con Polars (raw, sin headers) y devuelve lista 2D 1-based."""
    df = pl.read_excel(
        source=str(path),
        engine="calamine",
        has_header=False,
    )

    rows: list[list[Any]] = [[None]]  # row=0 sin usar
    for row_data in df.rows():
        row_vals: list[Any] = [None]  # col=0 sin usar
        row_vals.extend(row_data)
        rows.append(row_vals)

    return rows


def _normalizar_factura(valor: Any) -> str:
    """Normaliza un número de factura a string limpio."""
    if valor is None:
        return ""
    return str(valor).strip().upper()


def _normalizar_codigo(valor: Any) -> str:
    """Normaliza un código CUPS/procedimiento a string limpio.

    Maneja floats (Ej: 735301.0 → '735301') y cadenas con espacios.
    """
    if valor is None:
        return ""
    s = str(valor).strip().upper()
    # Sacar .0 de floats (Ej: 735301.0 → 735301)
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _max_date_col(rows: list[list[Any]], idx: int, data_start: int = 2) -> datetime | None:
    """Busca la fecha más alta en una columna (1-based), saltando nulos."""
    max_date: datetime | None = None
    for row in range(data_start, len(rows)):
        val = rows[row][idx]
        if val is None:
            continue
        if isinstance(val, datetime):
            d = val
        elif isinstance(val, str):
            # Intentar formatos comunes dd/mm/yyyy, yyyy-mm-dd
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    d = datetime.strptime(val.strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                continue
        elif isinstance(val, (int, float)):
            # Fecha serial de Excel
            from datetime import timedelta
            d = datetime(1899, 12, 30) + timedelta(days=int(val))
        else:
            continue
        if max_date is None or d > max_date:
            max_date = d
    return max_date


def _procesar_notas_enfermeria(path_notas: Path) -> dict[str, Any]:
    """Lee Notas Enfermería y busca traslados (OCF066).

    EMSSANAR se agrupa por Nº Identificación, el resto por factura.

    Returns:
        Dict con traslados_count, ocf066_rows (completa), max_fecha_nota.
    """
    rows = _leer_como_raw(path_notas)

    header_row = _detectar_fila_headers(rows, NOTAS_REQUIRED_HEADERS)
    if header_row is None:
        headers_detectados = [
            str(rows[1][c]) for c in range(1, len(rows[1]))
        ]
        return {
            "status": "error",
            "errors": [
                f"Notas Enfermería: no se encontraron las columnas "
                f"{list(NOTAS_REQUIRED_HEADERS.values())} en las primeras "
                f"{MAX_SCAN_ROWS} filas. "
                f"Headers fila 1: {headers_detectados}"
            ],
        }

    headers = [
        str(rows[header_row][c]) for c in range(1, len(rows[header_row]))
    ]
    indices, missing = get_column_indices(headers, NOTAS_REQUIRED_HEADERS)

    if missing:
        return {
            "status": "error",
            "errors": [
                f"Notas Enfermería: columnas no encontradas: {', '.join(missing)}. "
                f"Headers en fila {header_row}: {headers}"
            ],
        }

    # Opcionales
    opt_indices, _ = get_column_indices(headers, NOTAS_OPTIONAL_HEADERS)
    idx_entidad = opt_indices.get("entidad_administradora")
    idx_ident = opt_indices.get("identificacion")
    idx_fecha_nota = opt_indices.get("fecha_nota")

    idx_fact = indices["numero_factura"]
    idx_nota = indices["nota_enfermeria"]

    ocf066_rows: list[dict[str, Any]] = []
    facturas: list[str] = []
    pacientes_emssanar: list[str] = []
    data_start = header_row + 1

    for row in range(data_start, len(rows)):
        factura = _normalizar_factura(rows[row][idx_fact + 1])
        nota = str(rows[row][idx_nota + 1] or "").upper()

        if not factura:
            continue

        if "OCF066" not in nota:
            continue

        # EMSSANAR: matchear por identificación
        es_emssanar = (
            idx_entidad is not None
            and idx_ident is not None
            and str(rows[row][idx_entidad + 1] or "").strip().upper()
            == EMSSANAR_ENTIDAD.upper()
        )

        if es_emssanar:
            paciente = str(rows[row][idx_ident + 1] or "").strip().upper()
            if paciente:
                pacientes_emssanar.append(paciente)
                ocf066_rows.append({"factura": factura, "llave": paciente, "es_emssanar": True})
        else:
            facturas.append(factura)
            ocf066_rows.append({"factura": factura, "llave": factura, "es_emssanar": False})

    facturas_unicas = sorted(set(facturas))
    pacientes_unicos = sorted(set(pacientes_emssanar))
    total = len(facturas_unicas) + len(pacientes_unicos)

    logger.info(
        "Notas Enfermería: %d filas OCF066 (%d regulares, %d emssanar)",
        len(ocf066_rows), len(facturas_unicas), len(pacientes_unicos),
    )

    max_fecha_nota = _max_date_col(rows, idx_fecha_nota + 1, data_start) if idx_fecha_nota is not None else None

    return {
        "status": "success",
        "data": {
            "traslados_count": total,
            "ocf066_rows": ocf066_rows,
            "traslados_facturas": facturas_unicas,
            "traslados_emssanar_pacientes": pacientes_unicos,
            "max_fecha_nota": max_fecha_nota.isoformat() if max_fecha_nota else None,
        },
    }


def procesar_cruce(
    path_reporte: Path,
    path_ayudas: Path,
    path_notas: Path | None = None,
) -> dict[str, Any]:
    """Cruza los dos archivos y retorna lo no facturado.

    Args:
        path_reporte: Excel estándar (file 1)
        path_ayudas: Excel de ayudas diagnósticas (file 2)

    Returns:
        Dict con status, data (no_facturados, total_no_facturado, total_ayudas)
        o status error.
    """
    try:
        # ══════════════════════════════════════════════
        # REPORTE (Excel estándar)
        # ══════════════════════════════════════════════
        rows_reporte = _leer_como_raw(path_reporte)

        # Detectar fila de headers
        header_row_reporte = _detectar_fila_headers(rows_reporte, REPORTE_REQUIRED_HEADERS)
        if header_row_reporte is None:
            headers_detectados = [
                str(rows_reporte[1][c]) for c in range(1, len(rows_reporte[1]))
            ]
            return {
                "status": "error",
                "data": {},
                "errors": [
                    f"Reporte: no se encontraron las columnas "
                    f"{list(REPORTE_REQUIRED_HEADERS.values())} en las primeras "
                    f"{MAX_SCAN_ROWS} filas. "
                    f"Headers fila 1: {headers_detectados}"
                ],
            }

        headers_reporte = [
            str(rows_reporte[header_row_reporte][c])
            for c in range(1, len(rows_reporte[header_row_reporte]))
        ]
        indices_reporte, missing_reporte = get_column_indices(
            headers_reporte, REPORTE_REQUIRED_HEADERS
        )

        if missing_reporte:
            return {
                "status": "error",
                "data": {},
                "errors": [
                    f"Reporte: columnas no encontradas: {', '.join(missing_reporte)}. "
                    f"Headers en fila {header_row_reporte}: {headers_reporte}"
                ],
            }

        data_start_reporte = header_row_reporte + 1
        idx_fact_reporte = indices_reporte["numero_factura"]
        idx_codigo_reporte = indices_reporte["codigo"]
        idx_proc_reporte = indices_reporte["procedimiento"]
        idx_ident_reporte = indices_reporte["identificacion"]
        idx_fec_factura = indices_reporte["fec_factura"]

        # ══════════════════════════════════════════════
        # AYUDAS DIAGNÓSTICAS (formato nuevo)
        # ══════════════════════════════════════════════
        rows_ayudas = _leer_como_raw(path_ayudas)

        # Detectar fila de headers (solo columnas obligatorias)
        header_row = _detectar_fila_headers(rows_ayudas, AYUDAS_REQUIRED_HEADERS)
        if header_row is None:
            headers_detectados = [
                str(rows_ayudas[1][c]) for c in range(1, len(rows_ayudas[1]))
            ]
            return {
                "status": "error",
                "data": {},
                "errors": [
                    f"Ayudas Diagnósticas: no se encontraron las columnas "
                    f"{list(AYUDAS_REQUIRED_HEADERS.values())} en las primeras "
                    f"{MAX_SCAN_ROWS} filas. "
                    f"Headers fila 1: {headers_detectados}"
                ],
            }

        headers_ayudas = [
            str(rows_ayudas[header_row][c]) for c in range(1, len(rows_ayudas[header_row]))
        ]
        indices_ayudas, missing_ayudas = get_column_indices(
            headers_ayudas, AYUDAS_REQUIRED_HEADERS
        )

        if missing_ayudas:
            return {
                "status": "error",
                "data": {},
                "errors": [
                    f"Ayudas Diagnósticas: columnas no encontradas: {', '.join(missing_ayudas)}. "
                    f"Headers en fila {header_row}: {headers_ayudas}"
                ],
            }

        # Mapear columnas opcionales (no fallan si faltan)
        indices_opt_ayudas, _ = get_column_indices(
            headers_ayudas, AYUDAS_OPTIONAL_HEADERS
        )

        idx_fact_ayudas = indices_ayudas["numero_factura"]
        idx_cups_ayudas = indices_ayudas["cups"]
        idx_tipo_factura = indices_ayudas["tipo_factura_servicio"]
        idx_identificacion = indices_ayudas["identificacion"]
        idx_fecha_solicitud = indices_ayudas["fecha_solicitud"]
        idx_entidad_administradora = indices_ayudas["entidad_administradora"]
        idx_procedimiento_solicitado = indices_ayudas["procedimiento_solicitado"]
        idx_paciente = indices_opt_ayudas.get("paciente")
        idx_profesional_solicito = indices_opt_ayudas.get("profesional_solicito")

        # ══════════════════════════════════════════════
        # Totalizado por código
        # ══════════════════════════════════════════════
        # Contar ocurrencias de cada código en reporte y guardar nombre
        conteo_reporte: dict[str, int] = {}
        nombre_reporte: dict[str, str] = {}
        for row in range(data_start_reporte, len(rows_reporte)):
            codigo = _normalizar_codigo(rows_reporte[row][idx_codigo_reporte + 1])
            if codigo:
                conteo_reporte[codigo] = conteo_reporte.get(codigo, 0) + 1
                if codigo not in nombre_reporte:
                    nombre_reporte[codigo] = str(
                        rows_reporte[row][idx_proc_reporte + 1] or ""
                    ).strip().upper()

        logger.info("Códigos detectados en Reporte: %s", dict(sorted(conteo_reporte.items())))

        # Construir pares facturados en reporte (normal + emssanar por paciente)
        pares_normal: set[tuple[str, str]] = set()
        pares_emssanar: set[tuple[str, str]] = set()
        for row in range(data_start_reporte, len(rows_reporte)):
            factura = _normalizar_factura(rows_reporte[row][idx_fact_reporte + 1])
            codigo = _normalizar_codigo(rows_reporte[row][idx_codigo_reporte + 1])
            if factura and codigo:
                pares_normal.add((factura, codigo))
                paciente = str(rows_reporte[row][idx_ident_reporte + 1] or "").strip().upper()
                if paciente:
                    pares_emssanar.add((paciente, codigo))

        logger.info("Reporte: %d pares normal, %d pares emssanar", len(pares_normal), len(pares_emssanar))

        # Contar ocurrencias NO FACTURADAS de cada CUPS en ayudas (filtrado)
        # y guardar el nombre del procedimiento
        conteo_ayudas: dict[str, int] = {}
        conteo_ayudas_full: dict[str, int] = {}
        nombre_procedimiento: dict[str, str] = {}
        seen_conteo_ayudas: set[tuple[str, str]] = set()
        data_start = header_row + 1

        for row in range(data_start, len(rows_ayudas)):
            cups = _normalizar_codigo(rows_ayudas[row][idx_cups_ayudas + 1])
            tipo_factura = str(rows_ayudas[row][idx_tipo_factura + 1] or "").strip().upper()

            if tipo_factura not in ("URGENCIAS", "HOSPITALIZACIÓN"):
                continue
            if not cups:
                continue

            # Contar siempre (full) y solo si no está facturado
            factura = _normalizar_factura(rows_ayudas[row][idx_fact_ayudas + 1])
            conteo_ayudas_full[cups] = conteo_ayudas_full.get(cups, 0) + 1

            # Determinar si factura CAP → match por paciente
            es_cap = factura.startswith(CAP_PREFIX)
            if es_cap:
                paciente = str(rows_ayudas[row][idx_identificacion + 1] or "").strip().upper()
                if paciente and (paciente, cups) in pares_emssanar:
                    continue
                elif not paciente and (factura, cups) in pares_normal:
                    continue
            elif cups in CODIGOS_MATCH_POR_DOCUMENTO:
                # Match por documento Y por factura
                paciente = str(rows_ayudas[row][idx_identificacion + 1] or "").strip().upper()
                if paciente and (paciente, cups) in pares_emssanar:
                    continue
                if (factura, cups) in pares_normal:
                    continue
            else:
                if (factura, cups) in pares_normal:
                    continue

            # Dedup: mismo par factura+código cuenta una sola vez
            clave = (factura, cups)
            if clave in seen_conteo_ayudas:
                continue
            seen_conteo_ayudas.add(clave)

            conteo_ayudas[cups] = conteo_ayudas.get(cups, 0) + 1
            if cups not in nombre_procedimiento:
                    nombre_procedimiento[cups] = str(
                        rows_ayudas[row][idx_procedimiento_solicitado + 1] or ""
                    ).strip().upper()

        logger.info("Códigos detectados en Ayudas: %s", dict(sorted(conteo_ayudas.items())))

        # Armar totalizado combinado (4 categorías agregadas)
        totalizado: list[dict[str, Any]] = []
        total_excepciones_reporte = sum(
            conteo_reporte.get(c, 0) for c in CODIGOS_EXCEPCION
        )


        def _agregar_si_no_vacio(
            codigo: str, procedimiento: str,
            r: int, o: int, nf: int,
        ) -> None:
            if r > 0 or o > 0 or nf > 0:
                totalizado.append({
                    "codigo": codigo,
                    "procedimiento": procedimiento,
                    "total_reporte": r,
                    "total_ordenadas": o,
                    "total_no_facturado": nf,
                })

        # PARTO
        _agregar_si_no_vacio(
            "PARTO", "Procesados Parto",
            sum(conteo_reporte.get(c, 0) for c in PROCESADOS_PARTO),
            sum(conteo_ayudas_full.get(c, 0) for c in PROCESADOS_PARTO),
            sum(conteo_ayudas.get(c, 0) for c in PROCESADOS_PARTO),
        )

        # INTERCONSULTAS
        _agregar_si_no_vacio(
            "INTERCONSULTAS", "Procesados Interconsultas",
            sum(conteo_reporte.get(c, 0) for c in PROCESADOS_INTERCONSULTAS),
            sum(conteo_ayudas_full.get(c, 0) for c in PROCESADOS_INTERCONSULTAS),
            sum(conteo_ayudas.get(c, 0) for c in PROCESADOS_INTERCONSULTAS),
        )

        # OTROS
        _agregar_si_no_vacio(
            "OTROS", "Procesados Otros",
            sum(conteo_reporte.get(c, 0) for c in PROCESADOS_OTROS),
            sum(conteo_ayudas_full.get(c, 0) for c in PROCESADOS_OTROS),
            sum(conteo_ayudas.get(c, 0) for c in PROCESADOS_OTROS),
        )

        # Construir set de facturas del reporte con códigos de excepción
        excepcion_facturas_reporte: set[str] = set()
        excepcion_pacientes_reporte: set[str] = set()
        for row in range(data_start_reporte, len(rows_reporte)):
            factura = _normalizar_factura(rows_reporte[row][idx_fact_reporte + 1])
            codigo = _normalizar_codigo(rows_reporte[row][idx_codigo_reporte + 1])
            if factura and codigo and codigo in CODIGOS_EXCEPCION:
                excepcion_facturas_reporte.add(factura)
                paciente = str(rows_reporte[row][idx_ident_reporte + 1] or "").strip().upper()
                if paciente:
                    excepcion_pacientes_reporte.add(paciente)

        # Construir set de facturas con códigos de excepción en AYUDAS
        ayudas_excepcion_facturas: set[str] = set()
        for row in range(header_row + 1, len(rows_ayudas)):
            factura = _normalizar_factura(rows_ayudas[row][idx_fact_ayudas + 1])
            cups = _normalizar_codigo(rows_ayudas[row][idx_cups_ayudas + 1])
            tipo_factura = str(rows_ayudas[row][idx_tipo_factura + 1] or "").strip().upper()
            if factura and cups and cups in CODIGOS_EXCEPCION \
               and tipo_factura in ("URGENCIAS", "HOSPITALIZACIÓN"):
                ayudas_excepcion_facturas.add(factura)

        # ══════════════════════════════════════════════
        # Notas Enfermería (opcional)
        # ══════════════════════════════════════════════
        notas_data = None
        traslados_notas: set[str] = set()
        traslados_emssanar: set[str] = set()
        ocf066_rows: list[dict[str, Any]] = []
        if path_notas is not None:
            notas_result = _procesar_notas_enfermeria(path_notas)
            if notas_result["status"] == "success":
                notas_data = notas_result["data"]
                # Solo traslados cuya factura existe en ayudas con código de excepción
                todos_ocf066 = notas_data.get("ocf066_rows", [])
                ocf066_filtrados = [
                    r for r in todos_ocf066
                    if r["factura"] in ayudas_excepcion_facturas
                ]
                traslados_notas = {
                    r["factura"] for r in ocf066_filtrados if not r["es_emssanar"]
                }
                traslados_emssanar = {
                    r["llave"] for r in ocf066_filtrados if r["es_emssanar"]
                }
                ocf066_rows = ocf066_filtrados
                logger.info(
                    "Traslados en Notas: %d regulares + %d emssanar (filtrados contra ayudas)",
                    len(traslados_notas), len(traslados_emssanar),
                )
            else:
                logger.warning("Error en Notas Enfermería: %s", notas_result["errors"])

        # Fila Traslados en totalizado
        use_traslados = (
            total_excepciones_reporte > 0
            or (notas_data and (len(traslados_notas) > 0 or len(traslados_emssanar) > 0))
        )
        if use_traslados:
            if notas_data:
                total_ordenadas = len(traslados_notas) + len(traslados_emssanar)
                faltantes_regulares = traslados_notas - excepcion_facturas_reporte
                faltantes_emssanar = traslados_emssanar - excepcion_pacientes_reporte
                total_no_facturado = len(faltantes_regulares) + len(faltantes_emssanar)
            else:
                total_ordenadas = 0
                total_no_facturado = 0

            totalizado.append({
                "codigo": "TRASLADOS",
                "procedimiento": "Traslados (excepción)",
                "total_reporte": total_excepciones_reporte,
                "total_ordenadas": total_ordenadas,
                "total_no_facturado": total_no_facturado,
                "es_notas": notas_data is not None,
            })

        # ══════════════════════════════════════════════
        # No facturados: cruce ayudas (códigos normales)
        # ══════════════════════════════════════════════
        VISIBLE_CODES = PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS | PROCESADOS_OTROS
        no_facturados: list[dict[str, Any]] = []
        seen_no_facturados: set[tuple[str, str]] = set()
        data_start = header_row + 1

        for row in range(data_start, len(rows_ayudas)):
            factura = _normalizar_factura(rows_ayudas[row][idx_fact_ayudas + 1])
            cups = _normalizar_codigo(rows_ayudas[row][idx_cups_ayudas + 1])
            tipo_factura = str(rows_ayudas[row][idx_tipo_factura + 1] or "").strip().upper()

            if not factura:
                continue

            if tipo_factura not in ("URGENCIAS", "HOSPITALIZACIÓN"):
                continue

            # Solo códigos procesados: cruce ayudas vs reporte
            if cups and cups in VISIBLE_CODES:
                es_cap = factura.startswith(CAP_PREFIX)
                if es_cap:
                    paciente = str(rows_ayudas[row][idx_identificacion + 1] or "").strip().upper()
                    if paciente and (paciente, cups) in pares_emssanar:
                        continue
                    elif not paciente and (factura, cups) in pares_normal:
                        continue
                elif cups in CODIGOS_MATCH_POR_DOCUMENTO:
                    # Match por documento Y por factura
                    paciente = str(rows_ayudas[row][idx_identificacion + 1] or "").strip().upper()
                    if paciente and (paciente, cups) in pares_emssanar:
                        continue
                    if (factura, cups) in pares_normal:
                        continue
                elif (factura, cups) in pares_normal:
                    continue

                # Si ya agregamos esta factura con este código, skip (sale una vez)
                clave = (factura, cups)
                if clave in seen_no_facturados:
                    continue
                seen_no_facturados.add(clave)

                no_facturados.append({
                    "factura": rows_ayudas[row][idx_fact_ayudas + 1],
                    "cups": rows_ayudas[row][idx_cups_ayudas + 1],
                    "identificacion": rows_ayudas[row][idx_identificacion + 1],
                    "fecha_solicitud": rows_ayudas[row][idx_fecha_solicitud + 1],
                    "entidad_administradora": rows_ayudas[row][idx_entidad_administradora + 1],
                    "procedimiento_solicitado": rows_ayudas[row][idx_procedimiento_solicitado + 1],
                    "paciente": rows_ayudas[row][idx_paciente + 1] if idx_paciente is not None else "",
                    "tipo_factura_servicio": rows_ayudas[row][idx_tipo_factura + 1],
                    "profesional_solicito": rows_ayudas[row][idx_profesional_solicito + 1] if idx_profesional_solicito is not None else "",
                })

        # ══════════════════════════════════════════════
        # No facturados: traslados desde notas (solo si hay notas cargadas)
        # ══════════════════════════════════════════════
        if notas_data and ocf066_rows:
            # Construir lookup de ayudas por factura (códigos excepción)
            ayudas_x_factura: dict[str, dict[str, Any]] = {}
            for row in range(data_start, len(rows_ayudas)):
                factura = _normalizar_factura(rows_ayudas[row][idx_fact_ayudas + 1])
                cups = _normalizar_codigo(rows_ayudas[row][idx_cups_ayudas + 1])
                tipo_factura = str(rows_ayudas[row][idx_tipo_factura + 1] or "").strip().upper()

                if not factura or tipo_factura not in ("URGENCIAS", "HOSPITALIZACIÓN"):
                    continue
                if not cups or cups not in CODIGOS_EXCEPCION:
                    continue
                if factura not in ayudas_x_factura:
                    ayudas_x_factura[factura] = {
                        "factura": rows_ayudas[row][idx_fact_ayudas + 1],
                        "cups": rows_ayudas[row][idx_cups_ayudas + 1],
                        "identificacion": rows_ayudas[row][idx_identificacion + 1],
                        "fecha_solicitud": rows_ayudas[row][idx_fecha_solicitud + 1],
                        "entidad_administradora": rows_ayudas[row][idx_entidad_administradora + 1],
                        "procedimiento_solicitado": rows_ayudas[row][idx_procedimiento_solicitado + 1],
                        "paciente": rows_ayudas[row][idx_paciente + 1] if idx_paciente is not None else "",
                        "tipo_factura_servicio": rows_ayudas[row][idx_tipo_factura + 1],
                        "profesional_solicito": rows_ayudas[row][idx_profesional_solicito + 1] if idx_profesional_solicito is not None else "",
                    }

            # Recorrer cada fila OCF066 de notas
            for nota_row in ocf066_rows:
                factura_nota = nota_row["factura"]
                es_emssanar = nota_row["es_emssanar"]
                llave = nota_row["llave"]  # paciente si emssanar, factura si no

                # Match contra reporte: emssanar por paciente, resto por factura
                if es_emssanar:
                    if llave in excepcion_pacientes_reporte:
                        continue
                else:
                    if factura_nota in excepcion_facturas_reporte:
                        continue

                # Sacar datos de ayudas por factura (siempre por factura de la nota)
                if factura_nota in ayudas_x_factura:
                    entry = ayudas_x_factura[factura_nota]
                    clave = (
                        _normalizar_factura(entry["factura"]),
                        _normalizar_codigo(entry["cups"]),
                    )
                    if clave in seen_no_facturados:
                        continue
                    seen_no_facturados.add(clave)
                    no_facturados.append(entry)

        total_ayudas = max(0, len(rows_ayudas) - 1 - header_row)
        total_no_facturado = len(no_facturados)

        # ══════════════════════════════════════════════
        # Advertencia de fechas
        # ══════════════════════════════════════════════
        fecha_warning = None
        max_fecha_reporte = _max_date_col(rows_reporte, idx_fec_factura + 1, data_start_reporte)
        max_fecha_ayudas = _max_date_col(rows_ayudas, idx_fecha_solicitud + 1, header_row + 1)
        max_fecha_notas = (
            datetime.fromisoformat(notas_data["max_fecha_nota"])
            if notas_data and notas_data.get("max_fecha_nota")
            else None
        )

        # Comparar reporte vs ayudas
        if max_fecha_reporte and max_fecha_ayudas:
            diff = (max_fecha_ayudas - max_fecha_reporte).days
            if diff >= 1:
                fecha_warning = (
                    f"La fecha más reciente del Reporte ({max_fecha_reporte.date()}) "
                    f"es {diff} día(s) anterior a la de Ayudas ({max_fecha_ayudas.date()}). "
                    f"Pueden haber más faltantes no detectados."
                )

        # Comparar reporte vs notas (si aplica)
        if max_fecha_reporte and max_fecha_notas:
            diff_notas = (max_fecha_notas - max_fecha_reporte).days
            if diff_notas >= 1:
                notas_msg = (
                    f"La fecha más reciente del Reporte ({max_fecha_reporte.date()}) "
                    f"es {diff_notas} día(s) anterior a la de Notas ({max_fecha_notas.date()}). "
                    f"Pueden haber más traslados no detectados."
                )
                fecha_warning = f"{fecha_warning} {notas_msg}" if fecha_warning else notas_msg

        return {
            "status": "success",
            "data": {
                "totalizado": totalizado,
                "no_facturados": no_facturados,
                "total_no_facturado": total_no_facturado,
                "total_ayudas": total_ayudas,
                "notas_enfermeria": notas_data,
                "fecha_warning": fecha_warning,
            },
            "errors": [],
        }

    except Exception as e:
        logger.exception("Error procesando cruce")
        return {
            "status": "error",
            "data": {},
            "errors": [f"Error inesperado: {e}"],
        }
