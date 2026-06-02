FROM ghcr.io/astral-sh/uv:python3.13-trixie
WORKDIR /app

# Install runtime utilities natively
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the global workspace configurations
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/

# OPTIMIZATION: Extract ONLY backend packages out of the global lockfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --package backend

# Copy source code
COPY backend/ /app/backend/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

CMD ["prefect", "worker", "start", "--pool", "uk-health-pool"]
