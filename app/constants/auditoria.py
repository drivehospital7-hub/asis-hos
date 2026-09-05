"""Constants for the auditoria PDF extraction module.

All values resolve in order: environment variable → default.
"""

import os

TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "spa")
OCR_SCALE = float(os.getenv("OCR_SCALE", "2.0"))
