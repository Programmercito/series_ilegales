"""
ocr.py — Extrae el número de serie de un billete a partir de una imagen.

Usa pytesseract + Pillow con preprocesado para mejorar la lectura
de caracteres numéricos en imágenes de billetes.
"""
import re
import logging
from pathlib import Path

from PIL import Image, ImageFilter, ImageEnhance
import pytesseract

logger = logging.getLogger(__name__)

# Configuración de pytesseract: solo dígitos, modo página PSM 6 (bloque uniforme)
TESS_CONFIG = r"--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789"


def _preprocesar(img: Image.Image) -> Image.Image:
    """Pipeline de preprocesado para mejorar el OCR en números de billetes."""
    # 1. Escala de grises
    img = img.convert("L")

    # 2. Ampliar resolución si es pequeña
    w, h = img.size
    if w < 800:
        factor = 800 / w
        img = img.resize((int(w * factor), int(h * factor)), Image.LANCZOS)

    # 3. Aumentar contraste
    img = ImageEnhance.Contrast(img).enhance(2.5)

    # 4. Nitidez
    img = img.filter(ImageFilter.SHARPEN)

    # 5. Umbralización simple (binarizar)
    img = img.point(lambda p: 255 if p > 128 else 0)

    return img


def extraer_serie(ruta_imagen: str) -> str | None:
    """
    Abre la imagen, aplica preprocesado y extrae el número de serie.

    Devuelve:
        str  — texto crudo con los dígitos reconocidos  (>= 7 dígitos)
        None — si no se pudo extraer un número válido
    """
    try:
        img = Image.open(ruta_imagen)
    except Exception as e:
        logger.error("No se pudo abrir la imagen: %s", e)
        return None

    # Intentar primero con la imagen preprocesada
    for preprocesar in (True, False):
        imagen_a_usar = _preprocesar(img) if preprocesar else img.convert("L")
        texto = pytesseract.image_to_string(imagen_a_usar, config=TESS_CONFIG)
        solo_digitos = re.sub(r"\D", "", texto)
        logger.info(
            "OCR (%s): '%s' → dígitos: '%s'",
            "preprocesada" if preprocesar else "original",
            texto.strip(),
            solo_digitos,
        )
        if len(solo_digitos) >= 7:
            return solo_digitos

    logger.warning("OCR no extrajo suficientes dígitos de: %s", ruta_imagen)
    return None
