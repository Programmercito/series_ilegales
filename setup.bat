@echo off
:: ============================================================
:: setup.bat  —  Instala dependencias del verificador de billetes
:: ============================================================
echo.
echo  [1/4] Creando entorno virtual...
python -m venv venv
if errorlevel 1 (echo ERROR: No se pudo crear el venv. Verifica que Python 3.10+ este instalado. & exit /b 1)

echo  [2/4] Activando entorno virtual...
call venv\Scripts\activate.bat

echo  [3/4] Instalando dependencias Python...
venv\Scripts\pip install --upgrade pip -q
venv\Scripts\pip install -r requirements.txt

echo  [4/4] Verificando Tesseract-OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  AVISO: Tesseract-OCR no esta en el PATH.
    echo  Descargalo e instalalo desde:
    echo    https://github.com/UB-Mannheim/tesseract/wiki
    echo  Luego agrega C:\Program Files\Tesseract-OCR al PATH.
    echo.
) else (
    echo  Tesseract detectado OK.
)

echo.
echo  Setup completado.
echo  Configura tu token: copia .env.example a .env y edita BOT_TOKEN.
echo  Luego ejecuta:  run.bat
echo.
pause
