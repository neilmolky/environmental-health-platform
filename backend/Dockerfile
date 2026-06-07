# ============================================================================
# Base Runtime Setup
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.13-trixie
WORKDIR /app

# Install native core operating system utilities required for development/monitoring
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# PHASE 2: Metadata Caching (Speeds up DevContainer Rebuilds)
# ============================================================================
# CRITICAL: We must copy ALL workspace manifests required by the backend 
# so uv can reconstruct the local dependency graph before running a sync.
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml ./backend/
COPY utils/pyproject.toml ./utils/
COPY api/pyproject.toml ./api/
COPY frontend/pyproject.toml ./frontend/
COPY mock_services/pyproject.toml ./mock_services/

# DevContainer Target: We OMIT '--no-dev' here to ensure testing engines (pytest),
# linters (ruff), and debugging tools are fully available inside the container.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package backend
# ============================================================================
# PHASE 3: Source Injection & Workspace Linkage
# ============================================================================
# Inject the live source code into the isolated container space
COPY backend/ /app/backend/
COPY utils/ /app/utils/
COPY api/ /app/api/
COPY frontend/ /app/frontend/
COPY mock_services/ /app/mock_services/

# Final Sync: Re-run sync WITHOUT '--no-install-workspace' to natively wire
# 'backend' and 'utils' as active, editable packages in the virtual environment.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package backend

# ============================================================================
# PHASE 4: Runtime Environment Configuration
# ============================================================================
# Expose the virtual environment's binaries straight to the system path
ENV PATH="/app/.venv/bin:$PATH"

# Force Python stdout/stderr to be unbuffered to ensure real-time log tracking
ENV PYTHONUNBUFFERED=1

# Spin up the asynchronous Prefect execution worker agent targeting the regional pool
CMD ["prefect", "worker", "start", "--pool", "uk-health-pool"]
