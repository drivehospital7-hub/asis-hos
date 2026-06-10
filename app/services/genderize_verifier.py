"""Servicio para verificar sexo con Genderize API."""
import logging
import unicodedata
from dataclasses import dataclass

from app.services.genderize_extractor import ExtractResult, extract_factura_nombre_sexo
from app.services.genderize_service import _load_cache, predict_genders

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
    """Registro con discrepancia entre Excel y API."""

    numero_factura: str
    primer_apellido: str
    segundo_apellido: str
    primer_nombre: str
    segundo_nombre: str
    nombre_completo: str
    nombre_normalizado: str  # key del cache (solo Primer+Segundo nombre normalizado)
    sexo_excel: str  # M o F
    sexo_api: str  # male o female


def _normalize(name: str) -> str:
    """Normaliza nombre: minúsculas, sin tildes."""
    nfd = unicodedata.normalize("NFD", name)
    sin_tilde = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return sin_tilde.lower().strip()


def get_stats(excel_path: str) -> tuple[Stats, dict[str, ExtractResult], list[str]]:
    """Obtiene estadísticas sin hacer llamadas a la API.
    
    Returns:
        (estadisticas, mapa facturas, nombres_no_cache)
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
    
    # Contar cache hits
    cache_hits = sum(1 for n in unique_names if n in cache)
    
    # API calls necesarias
    api_calls = len(unique_names) - cache_hits
    
    # Construir lista de nombres_no_cache preservando orden de facturas
    nombres_no_cache = []
    for r in facturas.values():
        if r.nombre_normalizado not in cache:
            compound_name = (
                f"{r.primer_nombre} {r.segundo_nombre}".strip()
                if r.segundo_nombre
                else r.primer_nombre
            )
            nombres_no_cache.append(compound_name)
    
    stats = Stats(
        total_excel=len(resultados),
        nombres_unicos=len(unique_names),
        cache_hits=cache_hits,
        api_calls_necesarias=api_calls,
        rate_limit=None,
    )
    
    return stats, facturas, nombres_no_cache


def verificar_y_comparar(excel_path: str) -> tuple[Stats, list[Discrepancia]]:
    """Proceso completo: extraer, dedup, consultar API, comparar.
    
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
    
    # Separar en cache vs nuevos
    cache_hits = [n for n in unique_names if n in cache]
    nuevos = [n for n in unique_names if n not in cache]
    
    logger.info("Cache hits: %d, Nuevos: %d", len(cache_hits), len(nuevos))
    
    # Consultar API solo para los nuevos (en batches de 10)
    discrepancies = []
    all_results = {}
    
    # Resultados desde cache
    for name in cache_hits:
        cached = cache[name]
        # Buscar la factura asociada
        for f, r in facturas.items():
            if r.nombre_normalizado == name:
                all_results[f] = {
                    "sexo_excel": r.sexo,
                    "sexo_api": cached["gender"],
                }
                break
    
    # Consultar API para nuevos
    if nuevos:
        # Batches de 10
        for i in range(0, len(nuevos), 10):
            batch = nuevos[i:i+10]
            api_results, rate_limit = predict_genders(batch)
            
            for ar in api_results:
                # Buscar factura con este nombre normalizado
                for f, r in facturas.items():
                    if r.nombre_normalizado == _normalize(ar.name):
                        all_results[f] = {
                            "sexo_excel": r.sexo,
                            "sexo_api": ar.gender,
                        }
                        break
    
    # Comparar y buscar discrepancias
    for factura, datos in all_results.items():
        sexo_excel = datos["sexo_excel"]
        sexo_api = datos["sexo_api"]
        
        # Convertir: male->M, female->F
        sexo_api_code = "M" if sexo_api == "male" else "F"
        
        if sexo_excel != sexo_api_code:
            # Buscar nombre original
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
                    ))
                    break
    
    stats = Stats(
        total_excel=len(resultados),
        nombres_unicos=len(unique_names),
        cache_hits=len(cache_hits),
        api_calls_necesarias=len(nuevos),
        rate_limit=None,
    )
    
    logger.info("Discrepancias encontradas: %d", len(discrepancies))
    
    return stats, discrepancies