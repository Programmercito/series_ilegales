@echo off
:: ============================================================
:: run.bat  —  Inicia el bot de Telegram (long-polling)
:: ============================================================

:: Cargar .env si existe
if exist .env (
    setlocal EnableDelayedExpansion
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" (
            set "_key=%%A"
            if not "!_key:~0,1!"=="#" set %%A=%%B
        )
    )
)

if "%BOT_TOKEN%"=="" (
    echo ERROR: BOT_TOKEN no configurado.
    echo Copia .env.example a .env y pon tu token.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo  Bot iniciando... (Ctrl+C para detener)
python bot.py
