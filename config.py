import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Cada cuantos minutos se revisan las ofertas nuevas
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "10"))

# Ubicacion por defecto para las busquedas (ej: "España", "Remoto")
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "")

# Si las busquedas por defecto son solo remoto (f_WT=2)
DEFAULT_REMOTE = os.getenv("DEFAULT_REMOTE", "false").lower() == "true"

# Busquedas por defecto, separadas por coma
DEFAULT_KEYWORDS = os.getenv("DEFAULT_KEYWORDS", "python developer, data analyst")

# Ventana de tiempo: r86400 = ultimas 24h, r604800 = ultimos 7 dias
TIME_FILTER = os.getenv("TIME_FILTER", "r86400")

# Ruta del archivo de almacenamiento
STORAGE_PATH = os.getenv("STORAGE_PATH", "storage.json")

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit(
        "TELEGRAM_BOT_TOKEN no esta definido. "
        "Copia .env.example a .env y completa el token (o usa variables de entorno)."
    )
