# 🤖 Verificador de Billetes — Bot de Telegram

Bot que escanea el número de serie de un billete con OCR y verifica
si está dentro de los rangos reportados como ilegales (Bs.10, Bs.20, Bs.50).

---

## Flujo de conversación

```
/start
  └─ Elegir denominación (Bs10 / Bs20 / Bs50)
       └─ Enviar foto del número de serie
            └─ Confirmar número reconocido por OCR
                 ├─ ✅ Correcto  →  Verificar rango  →  🔴 INVÁLIDO / 🟢 VÁLIDO
                 └─ ❌ Incorrecto  →  Pedir otra foto
```

---

## Requisitos previos

| Herramienta | Versión mínima |
|-------------|---------------|
| Python      | 3.10+         |
| Tesseract OCR | 5.x         |

### Instalar Tesseract

- **Windows**: Descargar instalador de [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) y agregar `C:\Program Files\Tesseract-OCR` al `PATH`.
- **Ubuntu/Debian**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`

---

## Instalación

```bash
# Clonar / copiar el proyecto
cd series_ilegales

# Windows
setup.bat

# Linux / macOS
bash setup.sh
```

---

## Configuración

```bash
cp .env.example .env
# Editar .env y poner el token de @BotFather:
#   BOT_TOKEN=123456789:ABCdef...
```

---

## Ejecutar

```bash
# Windows
run.bat

# Linux / macOS
bash run.sh
```

El bot corre en **long-polling** (`getUpdates`) de forma continua.

---

## Estructura del proyecto

```
series_ilegales/
├── data/
│   └── ilegales.json      # Rangos de series ilegales (Bs10/Bs20/Bs50)
├── bot.py                 # Bot de Telegram (ConversationHandler)
├── ocr.py                 # Extracción OCR con pytesseract + Pillow
├── checker.py             # Verificación de rangos
├── requirements.txt
├── .env.example
├── setup.bat / setup.sh
└── run.bat / run.sh
```

---

## Variables de entorno

| Variable    | Descripción              |
|-------------|--------------------------|
| `BOT_TOKEN` | Token del bot de Telegram |

---

## Notas sobre el OCR

- Se realiza **preprocesado** (escala de grises → contraste → binarización) para mejorar la lectura.
- Si el OCR no extrae ≥ 7 dígitos, el bot pide una nueva foto automáticamente.
- El usuario **confirma** el número antes de verificarlo para evitar falsos resultados.
