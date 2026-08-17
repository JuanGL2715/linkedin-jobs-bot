import logging
from datetime import timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

import linkedin
from config import (
    DEFAULT_KEYWORDS,
    DEFAULT_LOCATION,
    DEFAULT_REMOTE,
    POLL_INTERVAL_MINUTES,
    STORAGE_PATH,
    TELEGRAM_BOT_TOKEN,
    TIME_FILTER,
)
from storage import Storage

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

storage = Storage(STORAGE_PATH)

HELP_TEXT = (
    "Bot de ofertas de LinkedIn\n\n"
    "Comandos:\n"
    "/add <palabras clave> [-l ubicacion] [-r] - agrega una busqueda\n"
    "  ejemplo: /add python developer -l Espana -r\n"
    "/list - lista las busquedas activas\n"
    "/remove <numero> - elimina una busqueda\n"
    "/search <palabras clave> - muestra ofertas ahora, sin guardar\n"
    "/check - fuerza la revision de ofertas ahora\n"
    "/status - estado del bot\n"
    "/help - esta ayuda\n\n"
    "Las ofertas nuevas se envian automaticamente a este chat."
)


def parse_search(text):
    tokens = text.split()
    remote = False
    location = DEFAULT_LOCATION
    keywords = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in ("-r", "--remote"):
            remote = True
        elif token in ("-l", "--location"):
            if i + 1 < len(tokens):
                location = tokens[i + 1]
                i += 1
        else:
            keywords.append(token)
        i += 1
    return {"keywords": " ".join(keywords), "location": location, "remote": remote}


def format_search(search):
    parts = [search["keywords"] or "(sin palabras clave)"]
    if search.get("location"):
        parts.append(search["location"])
    if search.get("remote"):
        parts.append("solo remoto")
    return " - ".join(parts)


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    chats = storage.get_chats()
    if not chats:
        logger.info("No hay chats registrados; no se notifica")
        return

    total_new = 0
    for search in storage.get_searches():
        try:
            jobs = linkedin.search_jobs(
                search["keywords"],
                location=search.get("location"),
                remote=search.get("remote", False),
                time_filter=TIME_FILTER,
            )
        except Exception as exc:
            logger.exception("Error buscando %s: %s", search["keywords"], exc)
            continue

        for job in jobs:
            if storage.is_seen(job.job_id):
                continue
            storage.mark_seen(job.job_id)
            for chat_id in chats:
                try:
                    await context.bot.send_message(
                        chat_id, linkedin.format_job(job), parse_mode="HTML"
                    )
                except Exception as exc:
                    logger.warning("No se pudo enviar al chat %s: %s", chat_id, exc)
            total_new += 1

    logger.info("Revision completada: %d ofertas nuevas", total_new)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    storage.add_chat(chat_id)
    await update.message.reply_text(
        "Hola! Te avisare cuando aparezcan nuevas ofertas de LinkedIn.\n\n"
        + HELP_TEXT
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def add_search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text[len("/add") :].strip()
    if not text:
        await update.message.reply_text(
            "Uso: /add <palabras clave> [-l ubicacion] [-r]\n"
            "Ejemplo: /add python developer -l Espana -r"
        )
        return
    search = parse_search(text)
    added = storage.add_search(search)
    if added:
        await update.message.reply_text(
            f"Busqueda agregada:\n{format_search(search)}\n\n"
            "Las nuevas ofertas se enviaran a este chat."
        )
    else:
        await update.message.reply_text("Esa busqueda ya existe.")


async def list_searches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    searches = storage.get_searches()
    if not searches:
        await update.message.reply_text("No hay busquedas. Usa /add para agregar una.")
        return
    lines = [f"{i + 1}. {format_search(s)}" for i, s in enumerate(searches)]
    await update.message.reply_text("Busquedas activas:\n\n" + "\n".join(lines))


async def remove_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /remove <numero>. Consulta /list.")
        return
    try:
        index = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("El numero debe ser entero.")
        return
    removed = storage.remove_search(index)
    if removed is None:
        await update.message.reply_text("Numero fuera de rango. Consulta /list.")
    else:
        await update.message.reply_text(
            f"Busqueda eliminada: {format_search(removed)}"
        )


async def search_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text[len("/search") :].strip()
    if not text:
        await update.message.reply_text("Uso: /search <palabras clave>")
        return
    search = parse_search(text)
    await update.message.reply_text(
        f"Buscando '{format_search(search)}'..."
    )
    try:
        jobs = linkedin.search_jobs(
            search["keywords"],
            location=search.get("location"),
            remote=search.get("remote", False),
            time_filter=TIME_FILTER,
            max_results=10,
        )
    except Exception as exc:
        await update.message.reply_text(f"Error al buscar: {exc}")
        return
    if not jobs:
        await update.message.reply_text("No se encontraron ofertas.")
        return
    for job in jobs[:10]:
        await update.message.reply_text(
            linkedin.format_job(job), parse_mode="HTML"
        )


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    storage.add_chat(update.effective_chat.id)
    await update.message.reply_text("Revisando ofertas...")
    await check_and_notify(context)
    await update.message.reply_text("Revision terminada.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats = storage.get_chats()
    searches = storage.get_searches()
    seen = len(storage.data["seen"])
    await update.message.reply_text(
        f"Chats registrados: {len(chats)}\n"
        f"Busquedas activas: {len(searches)}\n"
        f"Ofertas ya vistas: {seen}\n"
        f"Intervalo de revision: cada {POLL_INTERVAL_MINUTES} min"
    )


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("add", add_search_cmd))
    app.add_handler(CommandHandler("list", list_searches))
    app.add_handler(CommandHandler("remove", remove_search))
    app.add_handler(CommandHandler("search", search_now))
    app.add_handler(CommandHandler("check", check_now))
    app.add_handler(CommandHandler("status", status))

    for keywords in (k.strip() for k in DEFAULT_KEYWORDS.split(",") if k.strip()):
        storage.add_search(
            {
                "keywords": keywords,
                "location": DEFAULT_LOCATION,
                "remote": DEFAULT_REMOTE,
            }
        )

    app.job_queue.run_repeating(
        check_and_notify,
        interval=timedelta(minutes=POLL_INTERVAL_MINUTES),
        first=10,
    )

    logger.info("Bot iniciado. Revisando ofertas cada %d min", POLL_INTERVAL_MINUTES)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
