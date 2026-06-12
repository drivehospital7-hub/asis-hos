"""Servicio para verificar sexo con cache local (sin API)."""
import logging
from dataclasses import dataclass

from app.services.genderize_extractor import ExtractResult, extract_factura_nombre_sexo
from app.services.genderize_service import _load_cache, _classify

logger = logging.getLogger(__name__)


@dataclass
class Stats:
    """Estadísticas del proceso."""

    total_excel: int
    nombres_unicos: int
    cache_hits: int
    api_calls_necesarias: int
    rate_limit: dict | None


@dataclass
class Discrepancia:
    """Registro con discrepancia entre Excel y cache."""

    numero_factura: str
    primer_apellido: str
    segundo_apellido: str
    primer_nombre: str
    segundo_nombre: str
    nombre_completo: str
    nombre_normalizado: str  # key del cache (solo Primer+Segundo nombre normalizado)
    sexo_excel: str  # M o F
    sexo_api: str  # male o female
    numero_identificacion: str = ""  # Nº Identificación del Excel
    entidad_cobrar: str = ""  # Entidad Cobrar del Excel


def get_stats(excel_path: str) -> tuple[Stats, dict[str, ExtractResult], list[dict]]:
    """Obtiene estadísticas sin hacer llamadas a la API.
    
    Returns:
        (estadisticas, mapa facturas, nombres_no_cache) — nombres_no_cache es list[dict]
        con entries {"nombre": str, "sexo": str}.
    """
    # Extraer datos del Excel
    resultados = extract_factura_nombre_sexo(excel_path)
    
    # Cargar cache
    cache = _load_cache()
    
    # Agrupar por factura (tomar el primer nombre de cada factura)
    facturas = {}
    for r in resultados:
        if r.numero_factura not in facturas:
            facturas[r.numero_factura] = r
    
    # Nombres únicos
    unique_names = set(r.nombre_normalizado for r in facturas.values())
    
    # Separar "Hijo de"/"Hija de" — tienen género forzado, no necesitan API
    nombres_a_consultar: set[str] = set()
    nombres_hijo: set[str] = set()
    for n in unique_names:
        _, forced = _classify(n)
        if forced:
            nombres_hijo.add(n)
        else:
            nombres_a_consultar.add(n)
    
    # Contar cache hits solo sobre los que realmente irían a la API
    cache_hits = sum(1 for n in nombres_a_consultar if n in cache)
    
    # Construir lista de nombres_no_cache preservando orden de facturas
    # Se excluyen "Hijo de"/"Hija de" (tienen género forzado, no son "no cacheados")
    # Cada entry incluye nombre_normalizado y sexo del Excel
    # Se deduplica por nombre_normalizado
    nombres_no_cache = []
    seen: set[str] = set()
    for r in facturas.values():
        if r.nombre_normalizado in nombres_hijo:
            continue
        if r.nombre_normalizado not in cache and r.nombre_normalizado not in seen:
            nombres_no_cache.append({"nombre": r.nombre_normalizado, "sexo": r.sexo})
            seen.add(r.nombre_normalizado)
    
    no_cache = len(nombres_a_consultar) - cache_hits

    stats = Stats(
        total_excel=len(resultados),
        nombres_unicos=len(unique_names),
        cache_hits=cache_hits,
        api_calls_necesarias=no_cache,
        rate_limit=None,
    )
    
    return stats, facturas, nombres_no_cache


def verificar_y_comparar(excel_path: str) -> tuple[Stats, list[Discrepancia]]:
    """Proceso completo: extraer, dedup, consultar cache, comparar.
    
    Sin llamadas a API — solo cache local.
    
    Returns:
        (estadisticas, lista de discrepancias)
    """
    logger.info("Iniciando verificación de sexo")
    
    # Extraer datos del Excel
    resultados = extract_factura_nombre_sexo(excel_path)
    logger.info("Total extraídos del Excel: %d", len(resultados))
    
    # Agrupar por factura (tomar el primer nombre de cada factura)
    facturas = {}
    for r in resultados:
        if r.numero_factura not in facturas:
            facturas[r.numero_factura] = r
    
    # Deduplicar nombres únicos
    unique_names = list(set(r.nombre_normalizado for r in facturas.values()))
    logger.info("Nombres únicos: %d", len(unique_names))
    
    # Cargar cache
    cache = _load_cache()
    
    # Solo cache hits — nombres sin cache no generan discrepancia
    cache_hits = [n for n in unique_names if n in cache]
    logger.info("Cache hits: %d", len(cache_hits))
    
    discrepancies = []
    all_results = {}
    
    # Construir all_results desde cache
    for name in cache_hits:
        cached = cache[name]
        for f, r in facturas.items():
            if r.nombre_normalizado == name:
                all_results[f] = {
                    "sexo_excel": r.sexo,
                    "sexo_api": cached["gender"],
                }
                break
    
    # Comparar y buscar discrepancias
    for factura, datos in all_results.items():
        sexo_excel = datos["sexo_excel"]
        sexo_api = datos["sexo_api"]
        
        # Convertir: male->M, female->F, lastname->L, undefined->U
        # Cualquier otro valor -> ? (se muestra, no se salta)
        if sexo_api == "male":
            sexo_api_code = "M"
        elif sexo_api == "female":
            sexo_api_code = "F"
        elif sexo_api == "lastname":
            sexo_api_code = "L"
        elif sexo_api == "undefined":
            sexo_api_code = "U"
        else:
            sexo_api_code = "?"
        
        if sexo_excel != sexo_api_code:
            for f, r in facturas.items():
                if f == factura:
                    discrepancies.append(Discrepancia(
                        numero_factura=factura,
                        primer_apellido=r.primer_apellido,
                        segundo_apellido=r.segundo_apellido,
                        primer_nombre=r.primer_nombre,
                        segundo_nombre=r.segundo_nombre,
                        nombre_completo=r.nombre_completo,
                        nombre_normalizado=r.nombre_normalizado,
                        sexo_excel=sexo_excel,
                        sexo_api=sexo_api_code,
                        numero_identificacion=r.numero_identificacion,
                        entidad_cobrar=r.entidad_cobrar,
                    ))
                    break
    
    stats = Stats(
        total_excel=len(resultados),
        nombres_unicos=len(unique_names),
        cache_hits=len(cache_hits),
        api_calls_necesarias=len(unique_names) - len(cache_hits),
        rate_limit=None,
    )
    
    logger.info("Discrepancias encontradas: %d", len(discrepancies))
    
    return stats, discrepancies