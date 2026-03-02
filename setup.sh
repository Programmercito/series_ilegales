#!/usr/bin/env bash
# ============================================================
# setup.sh  —  Setup para Linux / macOS
# ============================================================
set -e

echo "[1/4] Creando entorno virtual..."
python3 -m venv venv

echo "[2/4] Activando entorno virtual..."
source venv/bin/activate

echo "[3/4] Instalando dependencias Python..."
pip install --upgrade pip -q
pip install -r requirements.txt

echo "[4/4] Verificando Tesseract-OCR..."
if ! command -v tesseract &>/dev/null; then
    echo ""
    echo "AVISO: Tesseract no encontrado. Instálalo con:"
    echo "  Ubuntu/Debian : sudo apt install tesseract-ocr"
    echo "  macOS (brew)  : brew install tesseract"
    echo ""
else
    echo "Tesseract detectado: $(tesseract --version 2>&1 | head -1)"
fi

echo ""
echo "Setup completado."
echo "1. Copia .env.example → .env  y configura BOT_TOKEN"
echo "2. Ejecuta:  bash run.sh"
