FROM ghcr.io/astral-sh/uv:0.11.21-python3.13-trixie
WORKDIR /workspace

# 1. add the location of the venv to the path
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 2. Copy the global workspace configurations
COPY pyproject.toml uv.lock ./
COPY mock/pyproject.toml /workspace/mock/
COPY utils/pyproject.toml /workspace/utils/

# 3. sync only required dependencies
RUN uv sync --frozen --no-dev --no-install-workspace --package mock

# 4. Copy source code into the active image workspace
COPY mock/ /workspace/mock/
COPY utils/ /workspace/utils/

# 5. Expose the service
EXPOSE 8001

# Generic fallback command. Overridden dynamically by orchestration
CMD ["python3"]
