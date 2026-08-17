# LinkedIn Jobs Telegram Bot

Bot de Telegram que monitorea búsquedas de ofertas en LinkedIn (scraping del
endpoint público de búsqueda) y te notifica automáticamente cuando aparece una
oferta nueva.

## Cómo funciona

- Cada intervalo (por defecto 10 minutos) revisa las búsquedas configuradas.
- Usa el endpoint público `jobs-guest/jobs/api/seeMoreJobPostings/search`, que
  no requiere iniciar sesión. Es scraping "ligero": no necesita navegador ni
  Playwright, por lo que consume muy poca RAM en producción.
- Solo envía ofertas nuevas (no repite las ya notificadas).

## Requisitos locales

- Python 3.10+ (probado con 3.14)
- Un bot de Telegram de [@BotFather](https://t.me/BotFather)

## Instalación y ejecución local

```bash
cd linkedin-jobs-bot
python -m venv .venv
.venv\Scripts\activate          # Windows
# o: source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

Edita `.env` y pon tu token:

```
TELEGRAM_BOT_TOKEN=tu_token_de_botfather
POLL_INTERVAL_MINUTES=10
DEFAULT_LOCATION=Espana
DEFAULT_REMOTE=true
DEFAULT_KEYWORDS=python developer, data analyst
TIME_FILTER=r86400
```

Ejecuta:

```bash
python bot.py
```

Abre tu bot en Telegram y envía `/start`. A partir de ahí recibirás las ofertas.

## Comandos

| Comando | Descripción |
| --- | --- |
| `/start` | Registra el chat y muestra la ayuda |
| `/add <palabras> [-l ubicación] [-r]` | Agrega una búsqueda. Ej: `/add python developer -l Espana -r` |
| `/list` | Lista búsquedas activas |
| `/remove <número>` | Elimina una búsqueda |
| `/search <palabras>` | Busca ahora (sin guardar) |
| `/check` | Fuerza la revisión ahora |
| `/status` | Estado del bot |
| `/help` | Ayuda |

## Despliegue

### Railway

1. Crea un proyecto nuevo y conéctalo al repo (o usa CLI + Docker).
2. Tupla `Variable` `TELEGRAM_BOT_TOKEN` con el token.
3. Railway detecta el `Dockerfile` automáticamente. CMD a `python bot.py`.
4. Despliega. El bot usa *polling*, así que no necesita URL pública.

Nota: en el plan gratuito el almacenamiento es efímero: al desplegar de nuevo se
pierden las búsquedas agregadas y el historial de ofertas ya vistas (no se
re-enviarán ofertas antiguas que estén fuera de la ventana `TIME_FILTER`).
Recomendación: define tus búsquedas en `DEFAULT_KEYWORDS` y, si quieres
persistencia real, monta un volumen en `/app`.

### Render

1. Crea un **Background Worker** (no un Web Service) y conéctalo al repo.
2. Enviroment: `Docker` (o usa el `Dockerfile`). Comando de arranque: `python bot.py`.
3. Agrega la variable `TELEGRAM_BOT_TOKEN`.
4. Despliega.

### Fly.io

```bash
fly launch --no-deploy --copy-config
fly secrets set TELEGRAM_BOT_TOKEN=tu_token
fly deploy
```

Ajusta `app` en `fly.toml` a un nombre único. No es necesario exponer puertos.

## Notas

- LinkedIn puede responder `403` si te detecta como bot (por frecuencia o IP).
  El scraper degrada de forma segura y reintenta en el siguiente ciclo.
- Para monitoreo en intervalos muy cortos usa `TIME_FILTER=r86400` y un
  `POLL_INTERVAL_MINUTES` bajo; respeta los límites para no ser bloqueado.
- La lista de ofertas ya vistas se conserva 30 días en `storage.json`.

## Estructura

```
linkedin-jobs-bot/
├── bot.py           # Bot de Telegram + planificador periódico
├── linkedin.py      # Scraper del endpoint público de LinkedIn
├── storage.py       # Persistencia en JSON (chats, búsquedas, ofertas vistas)
├── config.py        # Configuración vía variables de entorno
├── requirements.txt
├── Dockerfile
├── .env.example
└── .gitignore
```