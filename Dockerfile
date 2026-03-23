FROM python:3.13-slim

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# Copy application code
COPY src/ src/
COPY alembic.ini ./

# No CMD -- specified per service in docker-compose
