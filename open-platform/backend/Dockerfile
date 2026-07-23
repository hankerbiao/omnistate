FROM python:3.12-slim

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir \
      "mcp[cli]>=1.27,<2" \
      "fastapi>=0.115" \
      "uvicorn[standard]>=0.34" \
      "httpx>=0.28" \
      "pydantic>=2.10" \
      "loguru>=0.7.3"

COPY gateway_service ./gateway_service
COPY mcp_server ./mcp_server

RUN mkdir -p /data

EXPOSE 8820 8810

CMD ["python", "-m", "gateway_service"]
