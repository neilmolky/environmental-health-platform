FROM ghcr.io/astral-sh/uv:0.11.21-python3.13-trixie
WORKDIR /workspace

# 1. Update system baseline and install native geospatial C-libraries as root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates \
    gdal-bin libgdal-dev libgeos-dev libproj-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. add the location of the venv to the path
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 3. Copy the global workspace configurations
COPY pyproject.toml uv.lock ./
COPY frontend/pyproject.toml /workspace/frontend/
COPY utils/pyproject.toml /workspace/utils/

# 4. sync only required dependencies
RUN uv sync --frozen --no-dev --no-install-workspace --package frontend

# 5. Copy source code into the active image workspace
COPY frontend/ /workspace/frontend/
COPY utils/ /workspace/utils/

# 6. export uv dependencies to PATH and support log outputs for containers
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 7. Expose the service
EXPOSE 2718

# Generic fallback command. Overridden dynamically by docker-compose
CMD ["python3"]