# ============================================================================
# Runtime setup including DevContainer
# ============================================================================
FROM ghcr.io/astral-sh/uv:0.11.21-python3.13-trixie
WORKDIR /workspace

# 1. Install native core operating system utilities required for development/monitoring
# backend serves as an entrypoint for the dev-container, testing, and geospatial tasks
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates \
    # Native C-libraries required to compile/run geospatial tools like GeoPandas
    gdal-bin libgdal-dev libgeos-dev libproj-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. add the location of the venv to the path
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 3. Copy the global workspace configurations
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml /workspace/backend/
COPY utils/pyproject.toml /workspace/utils/
COPY api/pyproject.toml /workspace/api/
COPY frontend/pyproject.toml /workspace/frontend/
COPY mock/pyproject.toml /workspace/mock/

# 4. Sync only dependencies outside the workspace
RUN uv sync --frozen --no-install-workspace --all-packages

# 5. Copy workspace packages to enable code editing
COPY backend/ /workspace/backend/
COPY utils/ /workspace/utils/
COPY api/ /workspace/api/
COPY frontend/ /workspace/frontend/
COPY mock/ /workspace/mock/

# 6. sync with editable workspace dependencies.
RUN uv sync --frozen --all-packages

# Generic fallback command. Overridden dynamically by orchestration (docker-compose)
CMD ["python3"]
