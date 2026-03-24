# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trade-agent is an async Python trading agent pipeline that fetches market data (IDX stocks via yfinance, crypto via ccxt/Binance + CoinGecko fallback), validates and ingests it into TimescaleDB, and runs analysis/decision stages via LLM integration (litellm with gpt-4o-mini primary, Gemini fallback).

## Commands

```bash
# Install dependencies
uv sync                    # all deps including dev
uv sync --no-dev           # production only

# Run tests
pytest                     # all tests
pytest tests/test_data/    # specific module
pytest -x -vv              # stop on first failure, verbose

# Linting & formatting
ruff check src/ tests/     # lint check
ruff check src/ --fix      # auto-fix
ruff format src/ tests/    # format
mypy src/                  # type checking (strict mode)

# Pre-commit hooks
pre-commit run --all-files

# Full pre-commit check
pytest && ruff check --fix && ruff format && mypy src/

# Run pipeline
python -m src.pipeline.main                          # all stages, today
python -m src.pipeline.main --stage fetch            # single stage
python -m src.pipeline.main --date 2026-03-23        # specific date
python -m src.pipeline.main --rerun-failed           # retry failed assets

# Backfill historical data
python -m src.data.backfill --from 2024-01-01 --to 2026-03-23
python -m src.data.backfill --type crypto --assets BTC,ETH

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Bot service
python -m src.bot.main     # FastAPI on :8000

# Docker (TimescaleDB)
docker-compose up -d db
```