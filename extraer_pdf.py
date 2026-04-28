"""
Script de prueba para extraer texto de PDFs del módulo Derechos.
Uso: python extraer_pdf.py <archivo.pdf>
"""
import sys
from pathlib import Path

# Intentar con PyPDF2 (más rápido, para texto digital)
try:
    from pypdf import PdfReader
    print("Usando PyPDF2 (pypdf)")
    
    reader = PdfReader(sys.argv[1])
    print(f"Páginas: {len(reader.pages)}")
    print("-" * 50)
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        print(f"=== PÁGINA {i+1} ===")
        print(text[:2000] if text else "(vacío)")
        print()
    
except ImportError:
    print("PyPDF2 no instalado: pip install pypdf")
except Exception as e:
    print(f"Error: {e}")