FROM ghcr.io/astral-sh/uv:0.11.21-python3.13-trixie
WORKDIR /workspace

# 1. add the location of the venv to the path
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 2. Copy the global workspace configurations
COPY pyproject.toml uv.lock ./
COPY api/pyproject.toml /workspace/api/
COPY utils/pyproject.toml /workspace/utils/

# 3. sync only required dependencies
RUN uv sync --frozen --no-dev --no-install-workspace --package api

# 4. Copy source code into the active image workspace
COPY api/ /workspace/api/
COPY utils/ /workspace/utils/

# 5. export uv dependencies to PATH and support log outputs for containers
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 6. Expose the service
EXPOSE 8000

# Generic fallback command. Overridden dynamically by orchestration
CMD ["python3"]
