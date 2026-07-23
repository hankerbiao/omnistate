FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ARG HTTP_PROXY=http://10.2.48.65:7897
ARG HTTPS_PROXY=http://10.2.48.65:7897
ARG NO_PROXY=localhost,127.0.0.1,host.docker.internal,::1
ARG ALL_PROXY=socks5://10.2.48.65:7897
ARG UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:${PATH}" \
    HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    ALL_PROXY=${ALL_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY} \
    all_proxy=${ALL_PROXY} \
    UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX}

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --no-dev --no-install-project --default-index "${UV_DEFAULT_INDEX}"

COPY gateway_service ./gateway_service
COPY mcp_server ./mcp_server

RUN mkdir -p /data

EXPOSE 8820 8810

CMD ["python", "-m", "gateway_service"]
