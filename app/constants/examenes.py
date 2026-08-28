"""Constantes del módulo Exámenes (Lab Prefactura).

Catálogo por defecto (DEFAULT_EXAMENES), nombres de archivos de datos,
facturadores de respaldo y encabezados CSV.

DEFAULT_EXAMENES se copia VERBATIM desde ``D:\\CODE\\examenes\\examenes.json``
(66 entradas; los artefactos SDD mencionan 54 — discrepancia documentada en
apply-progress; la fuente es la verdad). Las escrituras del store respetan la
convención ``FLASK_DATA_SUFFIX`` del app standalone.
"""

from __future__ import annotations

# =============================================================================
# ARCHIVOS DE DATOS — nombres base (el store aplica FLASK_DATA_SUFFIX)
# =============================================================================

EX_EXAMENES_FILE: str = "examenes.json"
"""Archivo del catálogo (no-PHI, se commitea como seed)."""

EX_LISTADO_FILE: str = "listado.json"
"""Archivo del listado (PHI, copia manual de despliegue — nunca re-seed)."""

# =============================================================================
# FACTURADORES — respaldo hardcodeado del app fuente (EX-8)
# =============================================================================

FACTURADORES_FALLBACK: list[str] = [
    "Angie Chapuel",
    "Cataleya Tapia",
    "Silvia Ordoñez",
]

# =============================================================================
# CSV — encabezado exacto de exportación (EX-14)
# =============================================================================

CSV_HEADERS: list[str] = [
    "N°",
    "Paciente",
    "Cedula",
    "Codigo",
    "Examen",
    "NEPS",
    "MALLAM",
    "EMSS",
    "Facturador",
    "Fecha/Hora",
]

# =============================================================================
# CATÁLOGO POR DEFECTO — 66 entradas verbatim de la fuente (EX-5)
# =============================================================================

DEFAULT_EXAMENES: list[dict] = [
    { "cod": "903810", "emss": "", "mall": "", "neps": "X", "nom": "Calcio Semiautomatizado" },
    { "cod": "906205", "emss": "", "mall": "X", "neps": "", "nom": "Citomegalovirus Anticuerpos Ig G Semiautomatizado O Automatizado" },
    { "cod": "906206", "emss": "", "mall": "X", "neps": "", "nom": "Citomegalovirus Anticuerpos Ig M Semiautomatizado O Automatizado" },
    { "cod": "901210", "emss": "X", "mall": "", "neps": "", "nom": "Cultivo Especial Para Otros Microorganismos En Cualquier Muestra" },
    { "cod": "903859", "emss": "X", "mall": "X", "neps": "X", "nom": "Potasio En Suero U Otros Fluidos" },
    { "cod": "906243", "emss": "", "mall": "X", "neps": "", "nom": "Rubeola Anticuerpos Ig M Automatizado" },
    { "cod": "906241", "emss": "", "mall": "X", "neps": "X", "nom": "Rubeola Anticuerpos Ig G Automatizado" },
    { "cod": "902049", "emss": "X", "mall": "X", "neps": "X", "nom": "Tiempo De Tromboplastina Parcial [PTT]" },
    { "cod": "902045", "emss": "X", "mall": "X", "neps": "X", "nom": "Tiempo De Protrombina [PT]" },
    { "cod": "904921", "emss": "", "mall": "X", "neps": "AUTH", "nom": "Tiroxina Libre" },
    { "cod": "906131", "emss": "", "mall": "", "neps": "", "nom": "Trypanosoma Cruzi Anticuerpos Ig G Semiautomatizado O Automatizado" },
    { "cod": "906133", "emss": "", "mall": "", "neps": "", "nom": "Trypanosoma Cruzi Anticuerpos Ig M Semiautomatizado O Automatizado" },
    { "cod": "901235", "emss": "X", "mall": "X", "neps": "X", "nom": "Urocultivo (Antibiograma De Disco)" },
    { "cod": "903803", "emss": "X", "mall": "X", "neps": "X", "nom": "Albumina En Suero U Otros Fluidos" },
    { "cod": "903864", "emss": "X", "mall": "X", "neps": "X", "nom": "Sodio En Suero U Otros Fluidos" },
    { "cod": "903847", "emss": "X", "mall": "X", "neps": "", "nom": "Lipasa" },
    { "cod": "903865", "emss": "", "mall": "", "neps": "X", "nom": "Sodio En Orina De 24 Horas" },
    { "cod": "904925", "emss": "", "mall": "X", "neps": "", "nom": "Triyodotironina Total" },
    { "cod": "906220", "emss": "X", "mall": "", "neps": "", "nom": "Hepatitis B Anticuerpos Central Ig M [Anti-Core HBc-M] Semiautomatizado O Automatizado" },
    { "cod": "906221", "emss": "X", "mall": "", "neps": "", "nom": "Hepatitis B Anticuerpos Central Totales [Anti-Core HBc] Semiautomatizado O Automatizado" },
    { "cod": "903016", "emss": "AUTH", "mall": "AUTH", "neps": "AUTH", "nom": "Ferritina" },
    { "cod": "901101", "emss": "X", "mall": "X", "neps": "X", "nom": "Coloracion Acido Alcohol Resistente [Ziehl-Nielsen] Y Lectura O Baciloscopia" },
    { "cod": "903863", "emss": "X", "mall": "X", "neps": "X", "nom": "Proteinas Totales En Suero Y Otros Fluidos" },
    { "cod": "902210", "emss": "X", "mall": "", "neps": "X", "nom": "Hemograma IV [Hemoglobina, Hematocrito, Recuento De Eritrocitos, Indices Eritrocitarios]" },
    { "cod": "903862", "emss": "", "mall": "X", "neps": "X", "nom": "Proteinuria En Orina De 24 H" },
    { "cod": "906920", "emss": "AUTH", "mall": "AUTH", "neps": "AUTH", "nom": "Chlamydia Trachomatis Anticuerpos Ig M Semiautomatizado O Automatizado" },
    { "cod": "906019", "emss": "AUTH", "mall": "AUTH", "neps": "AUTH", "nom": "Chlamydia Trachomatis Anticuerpos Ig G Semiautomatizado O Automatizado" },
    { "cod": "906230", "emss": "X", "mall": "X", "neps": "X", "nom": "Herpes II Anticuerpos Ig G Manual, Semiautomatizado O Automatizado" },
    { "cod": "906231", "emss": "AUTH", "mall": "AUTH", "neps": "AUTH", "nom": "Herpes II Anticuerpos Ig M Manual, Semiautomatizado O Automatizado" },
    { "cod": "903867", "emss": "X", "mall": "X", "neps": "AUTH", "nom": "Transaminasa Glutamico Oxalacetica [Aspartato Amino Transferasa - AST]" },
    { "cod": "903866", "emss": "X", "mall": "X", "neps": "AUTH", "nom": "Transaminasa Glutamico-Pirurica [Alanino Amino Transferasa - ALT]" },
    { "cod": "906463", "emss": "AUTH", "mall": "AUTH", "neps": "AUTH", "nom": "Tiroideos Tiroglobulinicos Anticuerpos Automatizado" },
    { "cod": "902215", "emss": "X", "mall": "X", "neps": "X", "nom": "Hemograma VI Completo con Diferencial" },
    { "cod": "902035", "emss": "X", "mall": "X", "neps": "X", "nom": "Grupo Sangu\u00edneo ABO y Rh" },
    { "cod": "901010", "emss": "X", "mall": "X", "neps": "X", "nom": "Parcial De Orina [Uroan\u00e1lisis]" },
    { "cod": "904916", "emss": "", "mall": "X", "neps": "", "nom": "Prolactina" },
    { "cod": "904910", "emss": "", "mall": "X", "neps": "", "nom": "Hormona Luteinizante [LH]" },
    { "cod": "904911", "emss": "", "mall": "X", "neps": "", "nom": "Hormona Fol\u00edculo Estimulante [FSH]" },
    { "cod": "906610", "emss": "", "mall": "X", "neps": "", "nom": "antigeno especifico  para cancer de prostata" },
    { "cod": "906127", "emss": "", "mall": "X", "neps": "", "nom": "toxoplasma gondii ig g" },
    { "cod": "906129", "emss": "", "mall": "X", "neps": "", "nom": "toxoplasma gondii ig m" },
    { "cod": "908873", "emss": "", "mall": "X", "neps": "", "nom": "MYCOBACTERIUM TUBERCULOSIS IDENTIFICACI\u00d3N POR PRUEBAS MOLECULARES (ESPEC\u00cdFICO)" },
    { "cod": "901230", "emss": "X", "mall": "X", "neps": "", "nom": "Mycobacterium Tuberculosis Cultivo" },
    { "cod": "906223", "emss": "", "mall": "", "neps": "", "nom": "HEPATITIS B ANTIGENO DE SUPERFICIE (aC hbS)" },
    { "cod": "906225", "emss": "", "mall": "", "neps": "", "nom": "HEPATITIS C ANTICUERPOS HCV" },
    { "cod": "906247", "emss": "", "mall": "X", "neps": "", "nom": "VARICELA ZOSTER ANTICUERPOS IG G SEMIAUTOMATIZADO O AUTOMATIZADO" },
    { "cod": "906242", "emss": "", "mall": "X", "neps": "", "nom": "RUBEOLA ANTICUERPOS IG G SEMIAUTOMATIZADO" },
    { "cod": "901001", "emss": "X", "mall": "X", "neps": "", "nom": "ANTIBIOGRAMA ( DISCO )" },
    { "cod": "871020", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE COLUMNA TORACICA" },
    { "cod": "871040", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE COLUMNA LUMBOSACRA" },
    { "cod": "871030", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE COLUMNA DORSOLUMBAR" },
    { "cod": "873420", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE RODILLA AP. LATERAL U OBLICUA" },
    { "cod": "873422", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE RODILLA COMPARATIVAS" },
    { "cod": "872002", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE ABDOMEN SIMPLE" },
    { "cod": "873431", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE TOBILLO AP LATERAL Y ROTACION INTERNA" },
    { "cod": "871121", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE TORAX ( P. A. O A. P. Y LATERAL - DECUBITO LATERAL - OBLICUAS O LATERAL )" },
    { "cod": "873411", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE CADERA O ARTICULACION COXO-FEMORAL ( AP - LATERAL )" },
    { "cod": "873204", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE HOMBRO" },
    { "cod": "873333", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE PIE ( AP - LATERAL Y OBLICUA )" },
    { "cod": "870108", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE SENOS PARANASALES" },
    { "cod": "871050", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE SACRO COCCIX" },
    { "cod": "873112", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE CLAVICULA" },
    { "cod": "871010", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAFIA DE COLUMNA CERVICAL" },
    { "cod": "873210", "emss": "X", "mall": "X", "neps": "X", "nom": "RADIOGRAF\u00cdA DE MANO" },
    { "cod": "903856", "emss": "X", "mall": "", "neps": "", "nom": "NITROGENO UREICO ( BUN )" },
    { "cod": "903833", "nom": "FOSFATASA ALCALINA", "neps": "", "mall": "", "emss": "" },
]