"""Bot process entry point with health endpoint.

The bot process is separate from the pipeline process.
It MUST NOT import from src.pipeline or src.llm (two-process boundary).
"""

import uvicorn
from fastapi import FastAPI

from src.config import settings
from src.logging import setup_logging

app = FastAPI(title="Trade Agent Bot", docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for Docker and monitoring."""
    return {"status": "ok"}


def main() -> None:
    """Start the bot server."""
    setup_logging(settings.log_level, settings.log_format)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
