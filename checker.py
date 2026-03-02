"""
checker.py — Verifica si un número de serie cae en algún rango ilegal.
"""
import json
import re
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "ilegales.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    RANGOS: dict = json.load(f)


def limpiar_serie(texto: str) -> int | None:
    """
    Extrae solo los dígitos del texto OCR y lo convierte a entero.
    Devuelve None si no se pueden extraer al menos 7 dígitos.
    """
    solo_digitos = re.sub(r"\D", "", texto)
    if len(solo_digitos) < 7:
        return None
    return int(solo_digitos)


def check_serial(serial_texto: str, denominacion: str) -> tuple[bool, int | None]:
    """
    Verifica si la serie es inválida para la denominación dada.

    Retorna:
        (es_invalido: bool, numero_limpio: int | None)
        es_invalido=True  → billete ILEGAL
        es_invalido=False → billete OK
        numero_limpio=None → no se pudo parsear el número
    """
    numero = limpiar_serie(serial_texto)
    if numero is None:
        return False, None

    rangos = RANGOS.get(denominacion, [])
    for rango in rangos:
        if rango["del"] <= numero <= rango["al"]:
            return True, numero

    return False, numero


def check_serial_any(serial_texto: str) -> tuple[bool, int | None, str]:
    """
    Verifica si la serie es inválida.

    Formato esperado: "NNNNNNNN X"  (número + letra de serie)
    Solo la serie B se verifica contra los rangos ilegales.
    Cualquier otra letra es automáticamente válido.

    Retorna:
        (es_invalido: bool, numero_limpio: int | None, letra: str)
        es_invalido=True  → billete ILEGAL
        es_invalido=False → billete OK
        numero_limpio=None → no se pudo parsear el número
    """
    # Extraer letra de serie (última letra mayúscula del texto)
    letra_match = re.search(r'[A-Z]', serial_texto.upper())
    letra = letra_match.group(0) if letra_match else ""

    numero = limpiar_serie(serial_texto)
    if numero is None:
        return False, None, letra

    # Solo la serie B se coteja contra los rangos ilegales
    if letra != "B":
        return False, numero, letra

    for rangos in RANGOS.values():
        for rango in rangos:
            if rango["del"] <= numero <= rango["al"]:
                return True, numero, letra

    return False, numero, letra
