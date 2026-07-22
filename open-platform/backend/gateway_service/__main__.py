"""命令行启动入口。"""

from __future__ import annotations

import uvicorn

from .config import GatewaySettings


def main() -> None:
    settings = GatewaySettings.from_env()
    uvicorn.run(
        "gateway_service.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
