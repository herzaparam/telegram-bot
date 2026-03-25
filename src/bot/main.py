"""Bot process entry point with PTB webhook integration on FastAPI.

The bot process is separate from the pipeline process.
It MUST NOT import from src.pipeline or src.llm (two-process boundary).
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler

from src.bot.handlers.fundamentals import fundamentals_handler
from src.bot.handlers.lessons import lessons_handler
from src.bot.handlers.report import report_handler
from src.bot.handlers.scorecard import scorecard_handler
from src.bot.handlers.settings import settings_handler
from src.bot.handlers.start import start_handler
from src.bot.handlers.valuation import valuation_handler
from src.bot.handlers.watchlist import add_handler, remove_handler, watchlist_handler
from src.config import settings
from src.logging import setup_logging

logger = structlog.get_logger(__name__)

ptb_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Initialize PTB Application and set webhook on startup."""
    global ptb_app
    token = settings.telegram_bot_token.get_secret_value()
    if token:
        ptb_app = (
            Application.builder()
            .token(token)
            .updater(None)
            .build()
        )
        ptb_app.add_handler(CommandHandler("start", start_handler))
        ptb_app.add_handler(CommandHandler("add", add_handler))
        ptb_app.add_handler(CommandHandler("remove", remove_handler))
        ptb_app.add_handler(CommandHandler("watchlist", watchlist_handler))
        ptb_app.add_handler(CommandHandler("report", report_handler))
        ptb_app.add_handler(CommandHandler("scorecard", scorecard_handler))
        ptb_app.add_handler(CommandHandler("lessons", lessons_handler))
        ptb_app.add_handler(CommandHandler("settings", settings_handler))
        ptb_app.add_handler(CommandHandler("valuation", valuation_handler))
        ptb_app.add_handler(CommandHandler("fundamentals", fundamentals_handler))

        async with ptb_app:
            await ptb_app.start()
            if settings.webhook_base_url:
                webhook_url = f"{settings.webhook_base_url}/telegram/webhook"
                await ptb_app.bot.set_webhook(
                    url=webhook_url,
                    secret_token=settings.telegram_webhook_secret or None,
                )
                logger.info("webhook_set", url=webhook_url)
            yield
            await ptb_app.stop()
    else:
        logger.warning("no_bot_token", msg="TELEGRAM_BOT_TOKEN not set, bot disabled")
        yield

    ptb_app = None


app = FastAPI(title="Trade Agent Bot", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for Docker and monitoring."""
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> Response:
    """Receive Telegram webhook updates."""
    if ptb_app is None:
        return Response(status_code=503)
    if settings.telegram_webhook_secret:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret != settings.telegram_webhook_secret:
            return Response(status_code=403)
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response(status_code=200)


def main() -> None:
    """Start the bot server."""
    setup_logging(settings.log_level, settings.log_format)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
