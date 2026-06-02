FROM ghcr.io/astral-sh/uv:python3.13-trixie
WORKDIR /app

# Copy the global workspace configurations
COPY pyproject.toml uv.lock ./
COPY api/pyproject.toml api/

# OPTIMIZATION: Extract ONLY backend packages out of the global lockfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --package api

# Copy source code
COPY api/ /app/api/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
