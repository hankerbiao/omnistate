ARG PYTHON_BASE_IMAGE=python:3.13-slim-bookworm

FROM ${PYTHON_BASE_IMAGE} AS builder

ARG UV_VERSION=0.11.14

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/backend

RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}"

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


FROM ${PYTHON_BASE_IMAGE} AS runtime

ENV PATH="/app/backend/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DML_ENV=production \
    CONFIG_PATH=/run/dml/config.yaml \
    SKIP_INDEX_SYNC=1

WORKDIR /app/backend

RUN groupadd --system --gid 10001 dml \
    && useradd --system --uid 10001 --gid dml --home-dir /app/backend dml \
    && mkdir -p /app/backend/logs /run/dml \
    && chown -R dml:dml /app/backend /run/dml

COPY --from=builder --chown=dml:dml /app/backend/.venv ./.venv
COPY --chown=dml:dml backend/ ./
COPY --chown=dml:dml llms.txt /app/llms.txt

USER dml

EXPOSE 8801

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8801/health/ready', timeout=3).read()"]

CMD ["python", "-m", "app.main"]
