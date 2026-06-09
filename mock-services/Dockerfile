FROM ghcr.io/astral-sh/uv:python3.13-trixie
WORKDIR /app

# Copy the global workspace configurations
COPY pyproject.toml uv.lock ./
COPY mock-services/pyproject.toml ./mock-services/
COPY utils/pyproject.toml ./utils/

RUN apt-get update && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package mock-services

# Copy source code
COPY mock-services/ /app/mock-services/
COPY utils/ /app/utils/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8001
