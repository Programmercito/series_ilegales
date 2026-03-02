"""
bot.py — Bot de Telegram para verificar series de billetes venezolanos.

Flujo de conversación:
  /start → elegir denominación → enviar foto → confirmar OCR → resultado

Ejecución continua mediante long-polling (getUpdates).
"""
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
from checker import check_serial

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
SELECT_DENOM, SEND_PHOTO, CONFIRM_OCR = range(3)

# ──────────────────────────────────────────────
# Teclados reutilizables
# ──────────────────────────────────────────────
KB_DENOMINACION = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("💵 Bs. 10", callback_data="denom_Bs10"),
            InlineKeyboardButton("💵 Bs. 20", callback_data="denom_Bs20"),
            InlineKeyboardButton("💵 Bs. 50", callback_data="denom_Bs50"),
        ]
    ]
)

KB_CONFIRMACION = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("✅ Sí, es correcto", callback_data="ocr_si"),
            InlineKeyboardButton("📷 No, otra foto", callback_data="ocr_no"),
        ]
    ]
)

KB_REINICIAR = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🔄 Verificar otro billete", callback_data="reiniciar")]]
)


# ──────────────────────────────────────────────
# Handlers de conversación
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saludo inicial y selección de denominación."""
    nombre = update.effective_user.first_name or "amigo"
    await update.message.reply_text(
        f"👋 ¡Hola, *{nombre}*! Bienvenido al *Verificador de Billetes* 💰\n\n"
        "Soy tu asistente para comprobar si la serie de un billete "
        "está reportada como ilegal.\n\n"
        "¿Qué denominación quieres verificar?",
        parse_mode="Markdown",
        reply_markup=KB_DENOMINACION,
    )
    return SELECT_DENOM


async def seleccionar_denominacion(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Guarda la denominación elegida y pide la foto."""
    query = update.callback_query
    await query.answer()

    denominacion = query.data.replace("denom_", "")  # "Bs10" / "Bs20" / "Bs50"
    context.user_data["denom"] = denominacion

    await query.edit_message_text(
        f"✅ Denominación seleccionada: *{denominacion}*\n\n"
        "📸 Ahora envíame una foto clara del *número de serie* del billete.\n"
        "_Consejo: buena iluminación y encuadra solo los números._",
        parse_mode="Markdown",
    )
    return SEND_PHOTO


async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Descarga la foto, corre OCR y pide confirmación al usuario."""
    # Tomar la foto de mayor resolución que Telegram envía
    photo = update.message.photo[-1]
    file = await photo.get_file()

    # Guardar en archivo temporal
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        ruta_tmp = tmp.name

    await file.download_to_drive(ruta_tmp)
    logger.info("Foto guardada en %s", ruta_tmp)

    procesando_msg = await update.message.reply_text(
        "🔍 Procesando imagen con OCR, un momento…"
    )

    serie_raw = extraer_serie(ruta_tmp)

    # Eliminar archivo temporal
    try:
        os.unlink(ruta_tmp)
    except OSError:
        pass

    await procesando_msg.delete()

    if serie_raw is None:
        await update.message.reply_text(
            "⚠️ *No pude reconocer el número de serie* con claridad.\n\n"
            "Por favor envía otra foto:\n"
            "• Mayor iluminación\n"
            "• Enfocada directamente sobre los números\n"
            "• Sin reflejos ni sombras",
            parse_mode="Markdown",
        )
        return SEND_PHOTO  # pedir otra foto

    context.user_data["serie_raw"] = serie_raw

    await update.message.reply_text(
        f"🔢 Número reconocido: `{serie_raw}`\n\n"
        "¿Es este el número correcto?",
        parse_mode="Markdown",
        reply_markup=KB_CONFIRMACION,
    )
    return CONFIRM_OCR


async def confirmar_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """El usuario confirma o rechaza el número reconocido."""
    query = update.callback_query
    await query.answer()

    if query.data == "ocr_no":
        await query.edit_message_text(
            "📷 Entendido. Por favor envíame *otra foto* más clara del número de serie.",
            parse_mode="Markdown",
        )
        return SEND_PHOTO

    # ── Procesar y mostrar resultado ──
    serie_raw = context.user_data.get("serie_raw", "")
    denom = context.user_data.get("denom", "")

    es_invalido, numero = check_serial(serie_raw, denom)

    if numero is None:
        await query.edit_message_text(
            "❓ No pude interpretar ese número como entero. Intenta con otra foto.",
            reply_markup=KB_REINICIAR,
        )
        return ConversationHandler.END

    if es_invalido:
        mensaje = (
            "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n"
            "⛔   *BILLETE INVÁLIDO*   ⛔\n"
            "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n\n"
            f"❌  Serie:          `{numero}`\n"
            f"❌  Denominación:  *{denom}*\n\n"
            "🚫 Esta serie está reportada en la lista de\n"
            "    *billetes ILEGALES o falsificados*.\n\n"
            "⚠️  *NO ACEPTE este billete.*"
        )
    else:
        mensaje = (
            "🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢\n"
            "✅   *BILLETE VÁLIDO*   ✅\n"
            "🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢\n\n"
            f"✔️  Serie:          `{numero}`\n"
            f"✔️  Denominación:  *{denom}*\n\n"
            "👍 Esta serie *NO* aparece en la lista\n"
            "    de billetes ilegales.\n\n"
            "💚 *Puede aceptar este billete.*"
        )

    await query.edit_message_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=KB_REINICIAR,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Botón 'Verificar otro billete' — reinicia la conversación."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    await query.edit_message_text(
        "🔄 ¿Qué denominación quieres verificar ahora?",
        reply_markup=KB_DENOMINACION,
    )
    return SELECT_DENOM


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
            SELECT_DENOM: [
                CallbackQueryHandler(
                    seleccionar_denominacion, pattern=r"^denom_(Bs10|Bs20|Bs50)$"
                )
            ],
            SEND_PHOTO: [
                MessageHandler(filters.PHOTO, recibir_foto)
            ],
            CONFIRM_OCR: [
                CallbackQueryHandler(confirmar_ocr, pattern=r"^ocr_(si|no)$")
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            # Botón "Verificar otro" desde el resultado final
            CallbackQueryHandler(reiniciar, pattern=r"^reiniciar$"),
        ],
        # Permite al usuario reiniciar desde cualquier punto con /start
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    # Captura mensajes fuera de la conversación
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_fuera_de_contexto)
    )

    logger.info("🤖 Bot iniciado. Escuchando mensajes (Ctrl+C para detener)…")
    app.run_polling(
        poll_interval=1.0,          # consulta cada 1 segundo
        timeout=30,                 # timeout del getUpdates
        drop_pending_updates=True,  # ignora mensajes acumulados al arrancar
    )


if __name__ == "__main__":
    main()
