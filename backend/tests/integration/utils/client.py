"""Authenticated HTTP client wrapper for integration tests.

Provides a simpler interface for making authenticated API requests.
"""
from __future__ import annotations

from typing import Any

from httpx import AsyncClient, Response


class AuthenticatedClient:
    """Wrapper around httpx.AsyncClient with automatic Bearer token."""

    def __init__(self, client: AsyncClient, token: str):
        self._client = client
        self._token = token
        self._client.headers["Authorization"] = f"Bearer {token}"

    @property
    def client(self) -> AsyncClient:
        return self._client

    async def get(self, path: str, **kwargs: Any) -> Response:
        """Send GET request."""
        return await self._client.get(path, **kwargs)

    async def post(self, path: str, json: dict[str, Any] | None = None, **kwargs: Any) -> Response:
        """Send POST request with JSON body."""
        return await self._client.post(path, json=json, **kwargs)

    async def put(self, path: str, json: dict[str, Any] | None = None, **kwargs: Any) -> Response:
        """Send PUT request with JSON body."""
        return await self._client.put(path, json=json, **kwargs)

    async def patch(self, path: str, json: dict[str, Any] | None = None, **kwargs: Any) -> Response:
        """Send PATCH request with JSON body."""
        return await self._client.patch(path, json=json, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Response:
        """Send DELETE request."""
        return await self._client.delete(path, **kwargs)


def assert_response(response: Response, expected_status: int, message: str = "") -> dict[str, Any]:
    """Assert response status and return parsed JSON."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}. "
        f"{message}\n"
        f"Response: {response.text}"
    )
    return response.json()


def assert_success(response: Response, message: str = "") -> dict[str, Any]:
    """Assert response is successful (status < 400) and return parsed JSON."""
    assert response.status_code < 400, (
        f"Request failed with status {response.status_code}. "
        f"{message}\n"
        f"Response: {response.text}"
    )
    return response.json()


def get_data(response: Response) -> Any:
    """Extract data from API response."""
    return response.json()["data"]


def get_error(response: Response) -> dict[str, Any]:
    """Extract error from API response."""
    return response.json()["data"]