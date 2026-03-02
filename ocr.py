"""
ocr.py — Extrae el número de serie de un billete a partir de una imagen.

Usa pytesseract + Pillow con preprocesado para mejorar la lectura
de caracteres numéricos en imágenes de billetes.
"""
import re
import logging
import os
import sys
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import pytesseract

logger = logging.getLogger(__name__)

# Ruta explícita a Tesseract en Windows (por si no está en el PATH)
if sys.platform == "win32":
    _tess_candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for _path in _tess_candidates:
        if os.path.isfile(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            break

# Configs a probar en orden: PSM 7 = línea única, PSM 6 = bloque, PSM 13 = raw line
_CONFIGS = [
    r"--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    r"--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    r"--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    r"--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
]


def _escalar(img: Image.Image, ancho_min: int = 1200) -> Image.Image:
    w, h = img.size
    if w < ancho_min:
        factor = ancho_min / w
        img = img.resize((int(w * factor), int(h * factor)), Image.LANCZOS)
    return img


def _variantes(img: Image.Image):
    """Genera varias versiones preprocesadas de la imagen para mayor robustez."""
    gray = img.convert("L")
    gray = _escalar(gray)

    variantes = []

    # 1. Alto contraste + umbral Otsu-like (percentil 50)
    contraste = ImageEnhance.Contrast(gray).enhance(3.0)
    pixels = list(contraste.getdata())
    umbral = sorted(pixels)[len(pixels) // 2]
    binarizada = contraste.point(lambda p: 255 if p > umbral else 0)
    variantes.append(("binaria_otsu", binarizada))

    # 2. Imagen invertida (texto oscuro sobre fondo claro → fondo oscuro)
    variantes.append(("invertida", ImageOps.invert(binarizada)))

    # 3. Solo contraste + nitidez, sin binarizar
    nítida = ImageEnhance.Contrast(gray).enhance(2.0)
    nítida = nítida.filter(ImageFilter.SHARPEN)
    nítida = nítida.filter(ImageFilter.SHARPEN)
    variantes.append(("nitida", nítida))

    # 4. Escala de grises pura escalada
    variantes.append(("gris_puro", gray))

    return variantes


def extraer_serie(ruta_imagen: str) -> str | None:
    """
    Abre la imagen, prueba múltiples preprocesados + configs PSM y devuelve
    el candidato con más dígitos (mínimo 7).

    Devuelve:
        str  — dígitos reconocidos (>= 7)
        None — si no se pudo extraer un número válido
    """
    try:
        img = Image.open(ruta_imagen)
    except Exception as e:
        logger.error("No se pudo abrir la imagen: %s", e)
        return None

    mejor: str | None = None

    for nombre_var, imagen in _variantes(img):
        for config in _CONFIGS:
            try:
                texto = pytesseract.image_to_string(imagen, config=config)
            except Exception as e:
                logger.warning("Error OCR (%s, %s): %s", nombre_var, config, e)
                continue

            solo_digitos = re.sub(r"\D", "", texto)
            logger.info("OCR [%s | psm%s]: '%s' → '%s'",
                        nombre_var,
                        re.search(r"psm (\d+)", config).group(1),
                        texto.strip(),
                        solo_digitos)

    if len(solo_digitos) >= 7:
                # Buscar letra al final del texto (formato "NNNNN X")
                letra_match = re.search(r'[A-Z]\s*$', texto.strip())
                letra = letra_match.group(0).strip() if letra_match else ""
                candidato = solo_digitos + (" " + letra if letra else "")
                # Preferir el candidato más corto y plausible (7-12 dígitos)
                solo_digitos_actual = re.sub(r"\D", "", mejor) if mejor else ""
                if mejor is None or (
                    abs(len(solo_digitos) - 9) < abs(len(solo_digitos_actual) - 9)
                ):
                    mejor = candidato

    if mejor is None:
        logger.warning("OCR no extrajo suficientes dígitos de: %s", ruta_imagen)
    return mejor
