from typing import Any, Dict, Optional

import httpx

from ..core.config import get_settings

settings = get_settings()


class ApiClient:
    """Thin wrapper over HTTPX for the Telegram bot."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.api_gateway_url, timeout=10.0)

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = await self._client.post(path, json=json)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}

    async def close(self) -> None:
        await self._client.aclose()


api_client = ApiClient()
