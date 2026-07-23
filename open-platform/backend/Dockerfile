FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ARG UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:${PATH}" \
    UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX}

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --no-dev --no-install-project --default-index "${UV_DEFAULT_INDEX}"

COPY gateway_service ./gateway_service
COPY mcp_server ./mcp_server

RUN mkdir -p /data

EXPOSE 8820 8810

CMD ["python", "-m", "gateway_service"]
