"""
bot.py — Bot de Telegram para verificar series de billetes venezolanos.

Flujo de conversación:
  /start → enviar foto o escribir serie → (confirmar OCR si fue foto) → resultado

Ejecución continua mediante long-polling (getUpdates).
"""
import asyncio
import logging
import os
import tempfile

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ocr import extraer_serie
from checker import check_serial_any

# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PON_TU_TOKEN_AQUI")

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Estados de la conversación
# ──────────────────────────────────────────────
WAIT_INPUT, CONFIRM_OCR = range(2)

# ──────────────────────────────────────────────
# Teclados reutilizables
# ──────────────────────────────────────────────
KB_CONFIRMACION = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("✅ Sí, es correcto", callback_data="ocr_si"),
            InlineKeyboardButton("📷 No, otra foto", callback_data="ocr_no"),
        ]
    ]
)




# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def _mostrar_resultado(reply_fn, serie_raw: str) -> int:
    """Verifica la serie y envía el mensaje de resultado."""
    es_invalido, numero, letra = check_serial_any(serie_raw)

    serie_display = f"{numero} {letra}".strip() if numero else serie_raw

    if numero is None:
        await reply_fn(
            "❓ No pude interpretar ese número como entero.\n"
            "Intenta de nuevo con otra foto o escribe la serie manualmente."
        )
        return WAIT_INPUT

    if es_invalido:
        mensaje = (
            "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n"
            "⛔   *BILLETE INVÁLIDO*   ⛔\n"
            "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n\n"
            f"❌  Serie: `{serie_display}`\n\n"
            "🚫 Esta serie está reportada en la lista de\n"
            "    *billetes ILEGALES o falsificados*.\n\n"
            "⚠️  *NO ACEPTE este billete.*\n\n"
            "_Envíame otra serie cuando quieras._"
        )
    else:
        if letra and letra != "B":
            razon = f"Serie *{letra}* — no requiere verificación"
        else:
            razon = "No aparece en la lista de billetes ilegales"
        mensaje = (
            "🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢\n"
            "✅   *BILLETE VÁLIDO*   ✅\n"
            "🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢\n\n"
            f"✔️  Serie: `{serie_display}`\n"
            f"👍 {razon}\n\n"
            "💚 *Puede aceptar este billete.*\n\n"
            "_Envíame otra serie cuando quieras._"
        )

    await reply_fn(mensaje, parse_mode="Markdown")
    return WAIT_INPUT


# ──────────────────────────────────────────────
# Handlers de conversación
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saludo inicial — pide foto o serie de texto."""
    nombre = update.effective_user.first_name or "amigo"
    context.user_data.clear()
    await update.message.reply_text(
        f"👋 ¡Hola, *{nombre}*! Bienvenido al *Verificador de Billetes* 💰\n\n"
        "Envíame la serie del billete de una de estas formas:\n"
        "📸 *Una foto* del número de serie\n"
        "🔢 *Escribe* el número de serie directamente",
        parse_mode="Markdown",
    )
    return WAIT_INPUT


async def recibir_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """El usuario escribe la serie directamente — verificar al instante."""
    serie_raw = update.message.text.strip()
    return await _mostrar_resultado(
        lambda msg, **kw: update.message.reply_text(msg, **kw),
        serie_raw,
    )


async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Descarga la foto, corre OCR y pide confirmación al usuario."""
    photo = update.message.photo[-1]
    file = await photo.get_file()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        ruta_tmp = tmp.name

    await file.download_to_drive(ruta_tmp)
    logger.info("Foto guardada en %s", ruta_tmp)

    procesando_msg = await update.message.reply_text(
        "🔍 Procesando imagen con OCR, un momento…"
    )

    serie_raw = extraer_serie(ruta_tmp)

    try:
        os.unlink(ruta_tmp)
    except OSError:
        pass

    await procesando_msg.delete()

    if serie_raw is None:
        await update.message.reply_text(
            "⚠️ *No pude reconocer el número de serie* con claridad.\n\n"
            "Por favor intenta de nuevo:\n"
            "• Mayor iluminación\n"
            "• Enfocada directamente sobre los números\n"
            "• Sin reflejos ni sombras\n\n"
            "También puedes *escribir la serie* directamente.",
            parse_mode="Markdown",
        )
        return WAIT_INPUT

    context.user_data["serie_raw"] = serie_raw

    await update.message.reply_text(
        f"🔢 Número reconocido: `{serie_raw}`\n\n"
        "¿Es este el número correcto?",
        parse_mode="Markdown",
        reply_markup=KB_CONFIRMACION,
    )
    return CONFIRM_OCR


async def confirmar_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """El usuario confirma o rechaza el número reconocido por OCR."""
    query = update.callback_query
    await query.answer()

    if query.data == "ocr_no":
        await query.edit_message_text(
            "📷 Entendido. Envíame *otra foto* o *escribe la serie* directamente.",
            parse_mode="Markdown",
        )
        return WAIT_INPUT

    serie_raw = context.user_data.get("serie_raw", "")
    context.user_data.clear()
    return await _mostrar_resultado(
        lambda msg, **kw: query.edit_message_text(msg, **kw),
        serie_raw,
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    context.user_data.clear()
    await update.message.reply_text(
        "🛑 Operación cancelada.\n"
        "Usa /start cuando quieras verificar otro billete."
    )
    return ConversationHandler.END


async def mensaje_fuera_de_contexto(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Responde si el usuario envía algo sin haber iniciado la conversación."""
    await update.message.reply_text(
        "👋 Usa /start para comenzar a verificar billetes."
    )


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    if BOT_TOKEN == "PON_TU_TOKEN_AQUI":
        raise ValueError(
            "❌ Debes configurar el token del bot.\n"
            "   Exporta la variable de entorno BOT_TOKEN o edita bot.py."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            WAIT_INPUT: [
                MessageHandler(filters.PHOTO, recibir_foto),
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_texto),
            ],
            CONFIRM_OCR: [
                CallbackQueryHandler(confirmar_ocr, pattern=r"^ocr_(si|no)$")
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    # Captura mensajes fuera de la conversación
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_fuera_de_contexto)
    )

    logger.info("🤖 Bot iniciado. Escuchando mensajes (Ctrl+C para detener)…")
    app.run_polling(
        poll_interval=1.0,
        timeout=30,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
