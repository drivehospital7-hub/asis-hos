"""Constantes para el módulo Búsqueda PDF."""

import os

CONDICIONES = [
    "Conductor", "Ciclista", "Peatón", "Ocupante"
]

TRANSPORTES = [
    "Automóvil", "Bus", "Buseta", "Camión", "Camioneta",
    "Campero", "Microbus", "Tractocamion", "Motocicleta",
    "Motocarro", "Mototriciclo", "Cuatrimoto",
    "Moto extranjera", "Vehiculo extranjero", "Volqueta",
]

SINONIMOS_DEFAULT = {
    "Ocupante": ["Acompañante", "Pasajero"]
}

PDF_BASE_PATH = os.getenv("PDF_BASE_PATH", "C:\\")
