"""Servicio para manejo de hoja Revisión.

Este módulo detecta problemas en las facturas y los lista
en la hoja "Revision" para revisión manual.

Problemas detectados:
- Decimales: Facturas con valores decimales en Vlr. Subsidiado o Vlr. Procedimiento
- Doble tipo procedimiento: Facturas con más de un tipo de procedimiento
- Ruta duplicada: Pacientes con >= 3 facturas en Promoción y Prevención
- Convenio de procedimiento: Procedimientos que no corresponden al convenio
- Cantidades: Facturas con cantidades anómalas
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.constants import (
    CONVENIO_ASISTENCIAL,
    CONVENIO_PYP,
    REVISION_SHEET,
    REVISION_HEADERS,
    URGENCIA_REVISION_HEADERS,
    TARGET_PROCEDURES,
    RUTA_DUPLICADA_THRESHOLD,
    CANTIDAD_CONSULTAS_MIN,
    CANTIDAD_MAX,
    CANTIDAD_PYP_MIN,
    AREA_ODONTOLOGIA,
    AREA_URGENCIAS,
    CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO,
    LABORATORIO_NO,
    CENTRO_COSTO_APOYO_DIAGNOSTICO,
    CODIGOS_EXCEPTUADOS,
    URGENCIA_DATA_ROW_BACKGROUND_COLOR,
    CODIGOS_PYP_URGENCIAS,
    CENTRO_COSTO_PYP_URGENCIAS,
    CODIGOS_QUIROFANO_URGENCIAS,
    CENTRO_COSTO_QUIROFANO_URGENCIAS,
    CODIGOS_LABORATORIO_URGENCIAS,
    CENTRO_COSTO_LABORATORIO_URGENCIAS,
)
from app.utils.formatting import (
    create_header_style,
    create_data_row_style,
    create_urgencia_header_style,
    create_urgencia_data_row_style,
    auto_adjust_column_width,
)

logger = logging.getLogger(__name__)


def _normalize_header(value: Any) -> str:
    """Normaliza un header a minúsculas sin espacios extra."""
    return str(value).strip().lower() if value is not None else ""


def _normalize_invoice(value: Any) -> str | None:
    """Normaliza un número de factura a string."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and value == int(value):
        return str(int(value))
    return str(value).strip() or None


def _get_column_indices(headers: list[Any]) -> dict[str, int | None]:
    """
    Mapea nombres de columna a sus índices.
    
    Returns:
        Dict con nombre de columna -> índice (0-based) o None
    """
    indices: dict[str, int | None] = {
        "numero_factura": None,
        "vlr_subsidiado": None,
        "vlr_procedimiento": None,
        "codigo_tipo_procedimiento": None,
        "tipo_procedimiento": None,
        "codigo": None,
        "procedimiento": None,
        "identificacion": None,
        "convenio_facturado": None,
        "cantidad": None,
        "laboratorio": None,
        "centro_costo": None,
        "codigo_entidad_cobrar": None,
        "tipo_factura_descripcion": None,
        "ide_contrato": None,
        "tipo_identificacion": None,
        "fec_nacimiento": None,
        "fec_factura": None,
    }
    
    header_mapping = {
        ("número factura", "numero factura"): "numero_factura",
        ("vlr. subsidiado",): "vlr_subsidiado",
        ("vlr. procedimiento",): "vlr_procedimiento",
        ("código tipo procedimiento", "codigo tipo procedimiento"): "codigo_tipo_procedimiento",
        ("tipo procedimiento",): "tipo_procedimiento",
        ("código",): "codigo",
        ("procedimiento",): "procedimiento",
        ("nº identificación", "numero identificacion"): "identificacion",
        ("convenio facturado",): "convenio_facturado",
        ("cantidad",): "cantidad",
        ("laboratorio",): "laboratorio",
        ("centro costo",): "centro_costo",
        ("cód entidad cobrar",): "codigo_entidad_cobrar",
        ("tipo factura descripción",): "tipo_factura_descripcion",
        ("ide contrato",): "ide_contrato",
        ("tipo identificación", "tipo identificacion"): "tipo_identificacion",
        ("fec. nacimiento", "fecha nacimiento"): "fec_nacimiento",
        ("fec. factura", "fecha factura"): "fec_factura",
    }
    
    for i, header in enumerate(headers):
        normalized = _normalize_header(header)
        for variants, key in header_mapping.items():
            if normalized in variants:
                indices[key] = i
                break
    
    return indices


def _detect_decimals(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con valores decimales."""
    decimal_invoices = []
    
    num_fact_idx = indices["numero_factura"]
    vlr_sub_idx = indices["vlr_subsidiado"]
    vlr_proc_idx = indices["vlr_procedimiento"]
    
    if num_fact_idx is None:
        return []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        has_decimals = False
        
        if vlr_sub_idx is not None:
            vlr = data_sheet.cell(row=row, column=vlr_sub_idx + 1).value
            if isinstance(vlr, float) and vlr % 1 != 0:
                has_decimals = True
        
        if not has_decimals and vlr_proc_idx is not None:
            vlr = data_sheet.cell(row=row, column=vlr_proc_idx + 1).value
            if isinstance(vlr, float) and vlr % 1 != 0:
                has_decimals = True
        
        if has_decimals and factura_str not in decimal_invoices:
            decimal_invoices.append(factura_str)
            logger.debug("Factura %s con decimales detectada", factura_str)
    
    return decimal_invoices


def _detect_doble_tipo_procedimiento(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con más de un tipo de procedimiento."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    
    if num_fact_idx is None or tipo_proc_idx is None:
        return []
    
    tipo_por_factura: dict[str, set[str]] = {}
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        if tipo_value is not None:
            tipo_str = str(tipo_value).strip()
            if tipo_str:
                tipo_por_factura.setdefault(factura_str, set()).add(tipo_str)
    
    return [fact for fact, tipos in tipo_por_factura.items() if len(tipos) > 1]


def _detect_ruta_duplicada(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta pacientes con múltiples facturas en PyP."""
    num_fact_idx = indices["numero_factura"]
    ident_idx = indices["identificacion"]
    convenio_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, ident_idx, convenio_idx):
        return []
    
    conteo_ident: dict[str, set[str]] = defaultdict(set)
    
    for row in range(2, data_sheet.max_row + 1):
        convenio = data_sheet.cell(row=row, column=convenio_idx + 1).value
        if convenio != CONVENIO_PYP:
            continue
        
        ident = data_sheet.cell(row=row, column=ident_idx + 1).value
        factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        
        if ident is not None and factura is not None:
            ident_str = str(ident).strip()
            factura_str = str(factura).strip()
            if ident_str and factura_str:
                conteo_ident[ident_str].add(factura_str)
    
    return [
        ident for ident, facturas in conteo_ident.items()
        if len(facturas) >= RUTA_DUPLICADA_THRESHOLD
    ]


def _detect_convenio_procedimiento(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con procedimientos que no corresponden al convenio."""
    num_fact_idx = indices["numero_factura"]
    convenio_idx = indices["convenio_facturado"]
    proc_idx = indices["procedimiento"]
    
    if None in (num_fact_idx, convenio_idx, proc_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        convenio = data_sheet.cell(row=row, column=convenio_idx + 1).value
        procedimiento = data_sheet.cell(row=row, column=proc_idx + 1).value
        
        if procedimiento is None:
            continue
        
        proc_str = str(procedimiento).strip()
        should_add = False
        
        # Caso 1: Convenio Asistencial con procedimientos PyP
        if convenio == CONVENIO_ASISTENCIAL and proc_str in TARGET_PROCEDURES:
            should_add = True
            logger.debug(
                "Fila %s: Asistencial con procedimiento PyP: %s",
                row,
                proc_str,
            )
        
        # Caso 2: Convenio PyP con procedimientos NO PyP
        elif convenio == CONVENIO_PYP and proc_str not in TARGET_PROCEDURES:
            should_add = True
            logger.debug(
                "Fila %s: PyP con procedimiento diferente: %s",
                row,
                proc_str,
            )
        
        if should_add and factura_str not in problemas:
            problemas.append(factura_str)
    
    return problemas


def _detect_cantidades_anomalas(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con cantidades anómalas."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    cantidad_idx = indices["cantidad"]
    convenio_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, tipo_proc_idx, cantidad_idx, convenio_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        cantidad = data_sheet.cell(row=row, column=cantidad_idx + 1).value
        convenio = data_sheet.cell(row=row, column=convenio_idx + 1).value
        
        if not isinstance(cantidad, (int, float)):
            continue
        
        # Reglas de cantidad anómala
        is_anomaly = (
            # Consultas >= 2
            (tipo_value == "Consultas" and cantidad >= CANTIDAD_CONSULTAS_MIN)
            # Cualquier cantidad > 10
            or cantidad > CANTIDAD_MAX
            # PyP >= 3
            or (convenio == CONVENIO_PYP and cantidad >= CANTIDAD_PYP_MIN)
        )
        
        if is_anomaly and factura_str not in problemas:
            problemas.append(factura_str)
            logger.debug(
                "Fila %s: Cantidad anómala (Tipo: %s, Convenio: %s, Cant: %s)",
                row,
                tipo_value,
                convento,
                cantidad,
            )
    
    return problemas


def _detect_tipo_identificacion_edad(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, str]]:
    """
    Detecta facturas donde el tipo de identificación no coincide con la edad.
    
    Reglas:
    - < 7 años: RC (Registro Civil)
    - 7-17 años: TI (Tarjeta de Identidad)
    - >= 18 años: CC (Cédula de Ciudadanía)
    - Extranjeros < 18 años: MS
    - Extranjeros >= 18 años: AS
    
    Returns:
        Lista de dicts con keys: "factura", "tipo_actual", "tipo_deberia", "edad"
    """
    from datetime import datetime
    
    tipo_id_idx = indices["tipo_identificacion"]
    fec_nac_idx = indices["fec_nacimiento"]
    fec_fact_idx = indices["fec_factura"]
    num_fact_idx = indices["numero_factura"]
    
    if None in (tipo_id_idx, fec_nac_idx, fec_fact_idx, num_fact_idx):
        logger.warning(
            "No se pueden detectar errores de tipo identificación: "
            "columnas requeridas no encontradas. "
            "tipo_id=%s, fec_nac=%s, fec_fact=%s, num_fact=%s",
            tipo_id_idx, fec_nac_idx, fec_fact_idx, num_fact_idx
        )
        return []
    
    problemas = []
    facturas_ya_procesadas = set()
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str or factura_str in facturas_ya_procesadas:
            continue
        
        tipo_id = data_sheet.cell(row=row, column=tipo_id_idx + 1).value
        fec_nac = data_sheet.cell(row=row, column=fec_nac_idx + 1).value
        fec_fact = data_sheet.cell(row=row, column=fec_fact_idx + 1).value
        
        logger.debug(
            "Fila %s: tipo_id=%s, fec_nac=%s, fec_fact=%s",
            row, repr(tipo_id), repr(fec_nac), repr(fec_fact)
        )
        
        if not tipo_id or not fec_nac or not fec_fact:
            continue
        
        tipo_id_str = str(tipo_id).strip().upper()
        
        # Calcular edad
        try:
            # Intentar convertir fechas - varios formatos
            if isinstance(fec_nac, datetime):
                fecha_nac = fec_nac
            else:
                fec_nac_str = str(fec_nac).strip()
                # Intentar con formato fecha+hora primero
                try:
                    fecha_nac = datetime.strptime(fec_nac_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    fecha_nac = datetime.strptime(fec_nac_str, "%Y-%m-%d")
            
            if isinstance(fec_fact, datetime):
                fecha_fact = fec_fact
            else:
                fec_fact_str = str(fec_fact).strip()
                try:
                    fecha_fact = datetime.strptime(fec_fact_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    fecha_fact = datetime.strptime(fec_fact_str, "%Y-%m-%d")
            
            # Calcular edad en años
            edad = fecha_fact.year - fecha_nac.year
            if (fecha_fact.month, fecha_fact.day) < (fecha_nac.month, fecha_nac.day):
                edad -= 1
            
            logger.debug(
                "Fila %s: FechaNac=%s, FechaFact=%s, Edad calculada=%d",
                row, fecha_nac.date(), fecha_fact.date(), edad
            )
        except (ValueError, TypeError) as e:
            logger.debug("Fila %s: Error calculando edad: %s", row, e)
            continue
        
        # Determinar tipo correcto según edad
        tipo_correcto = None
        if tipo_id_str in ("RC", "TI", "CC"):
            if edad < 7:
                tipo_correcto = "RC"
            elif edad < 18:
                tipo_correcto = "TI"
            else:
                tipo_correcto = "CC"
        elif tipo_id_str in ("MS", "AS"):
            if edad < 18:
                tipo_correcto = "MS"
            else:
                tipo_correcto = "AS"
        
        logger.debug(
            "Fila %s: Edad=%d, Tipo actual=%s, Tipo correcto=%s",
            row, edad, tipo_id_str, tipo_correcto
        )
        
        # Si hay error, registrar
        if tipo_correcto and tipo_id_str != tipo_correcto:
            problemas.append({
                "factura": factura_str,
                "tipo_actual": tipo_id_str,
                "tipo_deberia": tipo_correcto,
                "edad": str(edad),
            })
            facturas_ya_procesadas.add(factura_str)
            logger.debug(
                "Fila %s: Tipo identificación incorrecto (Edad: %d, Tipo: %s, Debería: %s)",
                row,
                edad,
                tipo_id_str,
                tipo_correcto,
            )
    
    return problemas


def _detect_centro_costo_urgencias(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Detecta facturas con problemas de centro de costo y advertencias de derechos:
    -Regla 1: Código=02 Y Laboratorio=No Y Centro != APOYO DIAGNOSTICO-IMAGENOLOGIA
    -Regla 2: Código=14 Y Centro == TRASLADOS
    -Regla 3: Código en (990211, 890205, 890405, 861801) Y Centro != PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN
    -Regla 4: Código en (735301, 90DS02) Y Centro != QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO
    -Regla 5: Código en lista laboratorio Y Entidad=ESS118 Y Tipo=Intramural Y Centro != LABORATORIO CLINICO
    -Regla 5: Código en lista laboratorio Y Entidad=ESS118 Y Tipo=Intramural Y Centro != LABORATORIO CLINICO
    
    Returns:
        Lista de dicts con keys: "factura", "centro_actual", "centro_deberia"
    """
    from app.constants import (
        CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO,
        CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS,
        LABORATORIO_NO,
        CENTRO_COSTO_APOYO_DIAGNOSTICO,
        CENTRO_COSTO_TRASLADOS,
        CODIGOS_PYP_URGENCIAS,
        CENTRO_COSTO_PYP_URGENCIAS,
        CODIGOS_QUIROFANO_URGENCIAS,
        CENTRO_COSTO_QUIROFANO_URGENCIAS,
        CODIGOS_LABORATORIO_URGENCIAS,
        CENTRO_COSTO_LABORATORIO_URGENCIAS,
        CODIGO_IDE_CONTRATO_URGENCIAS,
        ENTIDAD_IDE_CONTRATO_URGENCIAS,
        IDE_CONTRATO_REQUERIDO_URGENCIAS,
    )
    
    num_fact_idx = indices["numero_factura"]
    codigo_tipo_proc_idx = indices.get("codigo_tipo_procedimiento")
    codigo_idx = indices.get("codigo")
    laboratorio_idx = indices.get("laboratorio")
    centro_costo_idx = indices.get("centro_costo")
    codigo_entidad_cobrar_idx = indices.get("codigo_entidad_cobrar")
    tipo_factura_descripcion_idx = indices.get("tipo_factura_descripcion")
    ide_contrato_idx = indices.get("ide_contrato")
    
    if num_fact_idx is None:
        return []
    
    # Si no tenemos las columnas necesarias, no podemos validar
    if codigo_tipo_proc_idx is None and laboratorio_idx is None and centro_costo_idx is None:
        logger.warning("No se encontraron columnas necesarias para validación de urgencias")
        return []
    
    problemas = []
    facturas_ya_procesadas = set()
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str or factura_str in facturas_ya_procesadas:
            continue
        
        # Obtener valores de las columnas
        codigo_tipo_proc = None
        if codigo_tipo_proc_idx is not None:
            codigo_tipo_proc = data_sheet.cell(row=row, column=codigo_tipo_proc_idx + 1).value
        
        codigo = None
        if codigo_idx is not None:
            codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        
        laboratorio = None
        if laboratorio_idx is not None:
            laboratorio = data_sheet.cell(row=row, column=laboratorio_idx + 1).value
        
        centro_costo = None
        if centro_costo_idx is not None:
            centro_costo = data_sheet.cell(row=row, column=centro_costo_idx + 1).value
        
        codigo_entidad_cobrar = None
        if codigo_entidad_cobrar_idx is not None:
            codigo_entidad_cobrar = data_sheet.cell(row=row, column=codigo_entidad_cobrar_idx + 1).value
        
        tipo_factura_descripcion = None
        if tipo_factura_descripcion_idx is not None:
            tipo_factura_descripcion = data_sheet.cell(row=row, column=tipo_factura_descripcion_idx + 1).value
        
        ide_contrato = None
        if ide_contrato_idx is not None:
            ide_contrato = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value
        
        # Normalizar strings
        codigo_str = str(codigo_tipo_proc).strip() if codigo_tipo_proc else ""
        codigo_excluir = str(codigo).strip() if codigo else ""
        laboratorio_str = str(laboratorio).strip() if laboratorio else ""
        centro_costo_str = str(centro_costo).strip() if centro_costo else ""
        codigo_entidad_str = str(codigo_entidad_cobrar).strip() if codigo_entidad_cobrar else ""
        tipo_factura_str = str(tipo_factura_descripcion).strip() if tipo_factura_descripcion else ""
        ide_contrato_str = str(ide_contrato).strip() if ide_contrato else ""
        
        # ----- Regla 1: Código=02 + Laboratorio=No + Centro !=IMAGENOLOGIA
        # (Independiente - con excepciones propias: no aplica a ciertos códigos)
        regla_1_activa = (
            codigo_str == CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO and
            laboratorio_str == LABORATORIO_NO
        )
        # Excepciones específicas de la Regla 1 (no afecta otras reglas)
        es_exceptuado = codigo_excluir in CODIGOS_EXCEPTUADOS
        if regla_1_activa and not es_exceptuado and centro_costo_str != CENTRO_COSTO_APOYO_DIAGNOSTICO:
            problemas.append({
                "factura": factura_str,
                "centro_actual": centro_costo_str,
                "centro_deberia": CENTRO_COSTO_APOYO_DIAGNOSTICO,
            })
            facturas_ya_procesadas.add(factura_str)
            logger.debug(
                "Fila %s: Código=02, Lab=No, Centroincorrecto (Centro: '%s')",
                row,
                centro_costo,
            )
        
        # ----- Regla 2: Código=14 + Centro Distinto a TRASLADOS
        # (Independiente)
        if codigo_str == CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS:
            if centro_costo_str != CENTRO_COSTO_TRASLADOS:
                problemas.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_TRASLADOS,
                })
                facturas_ya_procesadas.add(factura_str)
                logger.debug(
                    "Fila %s: Código=14, Centrodistinto a TRASLADOS",
                    row,
                )
        
        # ----- Regla 3: Código en (990211, 890205, 890405, 861801) + Centro != PROCEDIMIENTO PYP
        # (Independiente)
        if codigo_excluir in CODIGOS_PYP_URGENCIAS:
            if centro_costo_str != CENTRO_COSTO_PYP_URGENCIAS:
                problemas.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_PYP_URGENCIAS,
                })
                facturas_ya_procesadas.add(factura_str)
                logger.debug(
                    "Fila %s: Código=%s, Centro incorrecto (Centro: '%s')",
                    row,
                    codigo_excluir,
                    centro_costo_str,
                )
        
        # ----- Regla 4: Código en (735301, 90DS02) + Centro != QUIRÓFANOS
        # (Independiente)
        if codigo_excluir in CODIGOS_QUIROFANO_URGENCIAS:
            if centro_costo_str != CENTRO_COSTO_QUIROFANO_URGENCIAS:
                problemas.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_QUIROFANO_URGENCIAS,
                })
                facturas_ya_procesadas.add(factura_str)
                logger.debug(
                    "Fila %s: Código=%s, Centro incorrecto (Centro: '%s')",
                    row,
                    codigo_excluir,
                    centro_costo_str,
                )
        
        # ----- Regla 5: Código en lista laboratorio + Entidad=ESS118 + Tipo=Intramural -> Centro LABORATORIO
        # (Independiente)
        if codigo_excluir in CODIGOS_LABORATORIO_URGENCIAS:
            if codigo_entidad_str == "ESS118" and tipo_factura_str == "Intramural":
                centro_valido = centro_costo_str in (
                    CENTRO_COSTO_LABORATORIO_URGENCIAS,
                    f"{CENTRO_COSTO_LABORATORIO_URGENCIAS}.",
                )
                if not centro_valido:
                    problemas.append({
                        "factura": factura_str,
                        "centro_actual": centro_costo_str,
                        "centro_deberia": CENTRO_COSTO_LABORATORIO_URGENCIAS,
                    })
                    facturas_ya_procesadas.add(factura_str)
                    logger.debug(
                        "Fila %s: Código=%s, ESS118+Intramural, Centro incorrecto (Centro: '%s')",
                        row,
                        codigo_excluir,
                        centro_costo_str,
                    )
        
        # ----- Regla 6: Código=906340 + Cód Entidad Cobrar=EPSI05 -> IDE Contrato debe ser 986
        # (Independiente - NO depende de otras reglas)
        if codigo_excluir == CODIGO_IDE_CONTRATO_URGENCIAS and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_URGENCIAS:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_URGENCIAS:
                problemas.append({
                    "factura": factura_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_URGENCIAS,
                })
                facturas_ya_procesadas.add(factura_str)
                logger.debug(
                    "Fila %s: Código=%s, Entidad=%s, IDE Contrato incorrecto (IDE: '%s')",
                    row,
                    codigo_excluir,
                    codigo_entidad_str,
                    ide_contrato_str,
                )
    
    return problemas


def _write_column(sheet: Worksheet, column: int, values: list[str], start_row: int = 2) -> None:
    """Escribe una lista de valores en una columna."""
    for i, value in enumerate(values, start=start_row):
        sheet.cell(row=i, column=column, value=value)


def create_revision_sheet(
    workbook: Workbook,
    area: str = AREA_ODONTOLOGIA,
) -> dict[str, Any]:
    """
    Crea la hoja Revision con los problemas detectados.
    
    Args:
        workbook: Libro de Excel (debe tener una hoja activa con datos)
        area: Área del sistema ("odontologia" o "urgencias")
    
    Returns:
        Dict con información de los problemas encontrados
    """
    sheet = workbook.create_sheet(title=REVISION_SHEET)
    data_sheet = workbook.active
    
    # Insertar fila vacía arriba
    sheet.insert_rows(1)
    
    # Obtener índices de columnas
    headers = [
        data_sheet.cell(row=1, column=col).value
        for col in range(1, data_sheet.max_column + 1)
    ]
    indices = _get_column_indices(headers)
    
    # Seleccionar headers según el área
    if area == AREA_URGENCIAS:
        revision_headers = URGENCIA_REVISION_HEADERS
        header_style = create_urgencia_header_style()
    else:
        revision_headers = REVISION_HEADERS
        header_style = create_header_style()
    
    # Aplicar headers con estilo en fila 2
    for col, header in revision_headers.items():
        cell = sheet.cell(row=2, column=col, value=header)
        cell.font = header_style["font"]
        cell.fill = header_style["fill"]
        cell.border = header_style["border"]
        cell.alignment = header_style["alignment"]
    
    # Detectar problemas según el área
    if area == AREA_URGENCIAS:
        # Urgencias: enlistar facturas con problemas de centro de costo
        centros_costo = _detect_centro_costo_urgencias(data_sheet, indices)
        
        # Formatear para Excel: "FACTURA CENTRO_ACTUAL -> CENTRO_DEBERIA"
        centros_costo_str = [
            f"{item['factura']} {item['centro_actual']} -> {item['centro_deberia']}"
            for item in centros_costo
        ]
        
        # Escribir resultados en fila 3+
        _write_column(sheet, 1, centros_costo_str, start_row=3)
        
        # ParaJSON: strings formateados "FACTURA|CENTRO_ACTUAL|CENTRO_DEBERIA"
        problemas_encontrados = {
            "No se encuentra coincidencia con los siguientes centros de costos": [
                f"{item['factura']}|{item['centro_actual']}|{item['centro_deberia']}"
                for item in centros_costo
            ]
        }
    else:
        # Odontología: todas las validaciones existentes
        decimales = _detect_decimals(data_sheet, indices)
        doble_tipo = _detect_doble_tipo_procedimiento(data_sheet, indices)
        ruta_dup = _detect_ruta_duplicada(data_sheet, indices)
        conveniente_proc = _detect_convenio_procedimiento(data_sheet, indices)
        cantidades = _detect_cantidades_anomalas(data_sheet, indices)
        tipo_id_edad = _detect_tipo_identificacion_edad(data_sheet, indices)
        
        # Formatear para Excel: "FACTURA TIPO_ACTUAL -> TIPO_DEBERIA (Edad: X)"
        tipo_id_edad_str = [
            f"{item['factura']} {item['tipo_actual']} -> {item['tipo_deberia']} (Edad: {item['edad']})"
            for item in tipo_id_edad
        ]
        
        # Escribir resultados en fila 3+
        _write_column(sheet, 1, decimales, start_row=3)
        _write_column(sheet, 2, doble_tipo, start_row=3)
        _write_column(sheet, 3, ruta_dup, start_row=3)
        _write_column(sheet, 4, conveniente_proc, start_row=3)
        _write_column(sheet, 5, cantidades, start_row=3)
        _write_column(sheet, 6, tipo_id_edad_str, start_row=3)
        
        problemas_encontrados = {
            "Decimales": decimales,
            "Doble tipo procedimiento": doble_tipo,
            "Ruta Duplicada": ruta_dup,
            "Convenio de procedimiento": conveniente_proc,
            "Cantidades": cantidades,
            "Tipo Identificación": [item["factura"] for item in tipo_id_edad],
        }
    
    # Aplicar estilo a filas de datos (fila 3+) según el área
    if area == AREA_URGENCIAS:
        data_style = create_urgencia_data_row_style()
    else:
        data_style = create_data_row_style()
    
    for row in range(3, sheet.max_row + 1):
        for col in range(1, sheet.max_column + 1):
            cell = sheet.cell(row=row, column=col)
            cell.fill = data_style["fill"]
            cell.border = data_style["border"]
            cell.alignment = data_style["alignment"]
    
    # Ajustar ancho de columnas automáticamente
    column_widths = auto_adjust_column_width(sheet)
    
    # Logging según el área
    if area == AREA_URGENCIAS:
        logger.info(
            "Hoja Revision Urgencias creada - Centros de Costos: %d",
            len(centros_costo),
        )
    else:
        logger.info(
            "Hoja Revision Odontología creada - Decimales: %d, Doble tipo: %d, "
            "Ruta duplicada: %d, Convenio proc: %d, Cantidades: %d, Tipo ID: %d",
            len(decimales),
            len(doble_tipo),
            len(ruta_dup),
            len(conveniente_proc),
            len(cantidades),
            len(tipo_id_edad),
        )
    
    # Build resultado según el área
    if area == AREA_URGENCIAS:
        return {
            "rule": "create_revision_sheet",
            "sheet": REVISION_SHEET,
            "area": area,
            "headers": list(URGENCIA_REVISION_HEADERS.values()),
            "centros_de_costos_found": len(centros_costo),
            "problemas": problemas_encontrados,
            "column_widths": column_widths,
        }
    else:
        return {
            "rule": "create_revision_sheet",
            "sheet": REVISION_SHEET,
            "area": area,
            "headers": list(REVISION_HEADERS.values()),
            "decimal_invoices_found": len(decimales),
            "doble_tipo_invoices_found": len(doble_tipo),
            "ruta_duplicada_found": len(ruta_dup),
            "convenio_de_procedimiento_found": len(conveniente_proc),
            "cantidades_found": len(cantidades),
            "tipo_identificacion_found": len(tipo_id_edad),
            "problemas": problemas_encontrados,
            "column_widths": column_widths,
        }


def detect_all_problems(
    data_sheet: Worksheet,
    area: str = AREA_ODONTOLOGIA,
) -> dict[str, Any]:
    """
    Detecta todos los problemas en las facturas SIN crear hoja Excel.
    
    Esta función retorna los resultados para mostrarlos en el HTML del área.
    
    Args:
        data_sheet: Hoja de Excel con los datos
        area: Área del sistema ("odontologia" o "urgencias")
    
    Returns:
        Dict con los problemas encontrados por categoría
    """
    # Obtener índices de columnas
    headers = [
        data_sheet.cell(row=1, column=col).value
        for col in range(1, data_sheet.max_column + 1)
    ]
    indices = _get_column_indices(headers)
    
    if area == AREA_URGENCIAS:
        # Urgencias: detectar centros de costo y IDE Contrato
        problemas_todos = _detect_centro_costo_urgencias(data_sheet, indices)
        
        # Separar en dos listas: centros de costo vs IDE Contrato
        centros_costo = []
        ide_contrato = []
        for item in problemas_todos:
            if "centro_actual" in item and "centro_deberia" in item:
                centros_costo.append(item)
            elif "ide_contrato_actual" in item and "ide_contrato_deberia" in item:
                ide_contrato.append(item)
        
        return {
            "area": area,
            "problemas": {
                "centros_de_costos": [
                    {
                        "factura": item["factura"],
                        "centro_actual": item["centro_actual"],
                        "centro_deberia": item["centro_deberia"],
                    }
                    for item in centros_costo
                ],
                "ide_contrato": [
                    {
                        "factura": item["factura"],
                        "ide_contrato_actual": item["ide_contrato_actual"],
                        "ide_contrato_deberia": item["ide_contrato_deberia"],
                    }
                    for item in ide_contrato
                ],
            },
            "totales": {
                "centros_de_costos": len(centros_costo),
                "ide_contrato": len(ide_contrato),
            }
        }
    else:
        # Odontología: todas las validaciones
        decimales = _detect_decimals(data_sheet, indices)
        doble_tipo = _detect_doble_tipo_procedimiento(data_sheet, indices)
        ruta_dup = _detect_ruta_duplicada(data_sheet, indices)
        conveniente_proc = _detect_convenio_procedimiento(data_sheet, indices)
        cantidades = _detect_cantidades_anomalas(data_sheet, indices)
        tipo_id_edad = _detect_tipo_identificacion_edad(data_sheet, indices)
        
        return {
            "area": area,
            "problemas": {
                "decimales": decimales,
                "doble_tipo_procedimiento": doble_tipo,
                "ruta_duplicada": ruta_dup,
                "convenio_procedimiento": conveniente_proc,
                "cantidades_anomalas": cantidades,
                "tipo_identificacion_edad": tipo_id_edad,
            },
            "totales": {
                "decimales": len(decimales),
                "doble_tipo_procedimiento": len(doble_tipo),
                "ruta_duplicada": len(ruta_dup),
                "convenio_procedimiento": len(conveniente_proc),
                "cantidades_anomalas": len(cantidades),
                "tipo_identificacion_edad": len(tipo_id_edad),
            }
        }
