FROM ghcr.io/astral-sh/uv:python3.13-trixie
WORKDIR /app

# Copy the global workspace configurations
COPY pyproject.toml uv.lock ./
COPY mock_services/pyproject.toml ./mock_services/
COPY utils/pyproject.toml ./utils/

RUN apt-get update && apt-get upgrade -y \
    && --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package mock_services

# Copy source code
COPY mock_services/ /app/mock_services/
COPY utils/ /app/utils/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "mock_services.main:app", "--host", "0.0.0.0", "--port", "8000"]
