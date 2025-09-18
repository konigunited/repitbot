from typing import Any, Dict, Optional

import httpx

from ..core.config import get_settings

settings = get_settings()


class ProxyService:
    """Forward requests from the gateway to downstream services."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=settings.request_timeout)

    async def request(
        self,
        service: str,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        base_url = settings.upstream_services.get(service)
        if not base_url:
            raise ValueError(f"Unknown upstream service: {service}")
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        response = await self._client.request(method=method.upper(), url=url, params=params, json=json, headers=headers)
        return response

    async def close(self) -> None:
        await self._client.aclose()


proxy_service = ProxyService()
