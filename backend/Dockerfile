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
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml ./backend/
COPY utils/pyproject.toml ./utils/
COPY api/pyproject.toml ./api/
COPY frontend/pyproject.toml ./frontend/
COPY mock_services/pyproject.toml ./mock_services/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --all-packages

# ============================================================================
# PHASE 3: Source Injection & Workspace Linkage
# ============================================================================
# Inject the live source code into the isolated container space.
# Since this layer comes AFTER the heavy download step, code changes here 
# will bypass the download phase and compile instantly!
COPY backend/ /app/backend/
COPY utils/ /app/utils/
COPY api/ /app/api/
COPY frontend/ /app/frontend/
COPY mock_services/ /app/mock_services/

# Final local compilation: links your actual workspace packages into the environment.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-packages

# ============================================================================
# PHASE 4: Runtime Environment Configuration
# ============================================================================
# Expose the virtual environment's binaries straight to the system path
ENV PATH="/app/.venv/bin:$PATH"

# Force Python stdout/stderr to be unbuffered to ensure real-time log tracking
ENV PYTHONUNBUFFERED=1

# Spin up the asynchronous Prefect execution worker agent targeting the regional pool
CMD ["prefect", "worker", "start", "--pool", "uk-health-pool"]
