# Stage 1: Build frontend and install native geospatial C-libraries
FROM ghcr.io/astral-sh/uv:python3.13-trixie AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install required C-binaries for compiling spatial packages (GeoPandas/Fiona)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libgeos-dev libproj-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY frontend/pyproject.toml frontend/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --package frontend

# Stage 2: Clean, optimized Frontend Runtime
FROM python:3.13-slim-trixie
WORKDIR /app

# FIX: Core dynamic runtime library identifiers updated for Debian Trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal36 \
    libgeos-c1t64 \
    libproj25 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY frontend/ /app/frontend/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 2718
CMD ["marimo", "run", "frontend/health_analysis.py", "--host", "0.0.0.0", "--port", "2718"]