#!/usr/bin/env bash
# ============================================================
# run.sh  —  Inicia el bot (Linux / macOS)
# ============================================================
set -e

# Cargar .env si existe
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: BOT_TOKEN no configurado."
    echo "Copia .env.example a .env y pon tu token."
    exit 1
fi

source venv/bin/activate
echo "Bot iniciando... (Ctrl+C para detener)"
python bot.py
