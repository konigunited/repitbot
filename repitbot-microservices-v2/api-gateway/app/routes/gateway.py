from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from ..services.proxy import proxy_service

router = APIRouter()


@router.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(service: str, path: str, request: Request) -> Response:
    body: Dict[str, Any] | None = None
    if request.method in {"POST", "PUT", "PATCH"}:
        if request.headers.get("content-type", "").startswith("application/json"):
            body = await request.json()
        else:
            body = None
    params = dict(request.query_params)
    headers = {key: value for key, value in request.headers.items() if key.lower().startswith("x-") or key.lower() == "authorization"}

    try:
        response = await proxy_service.request(
            service=service,
            method=request.method,
            path=path,
            params=params,
            json=body,
            headers=headers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    content_type = response.headers.get("content-type", "application/json")
    content = None
    if response.content:
        if "application/json" in content_type:
            content = response.json()
            return JSONResponse(status_code=response.status_code, content=content)
        content = response.text
    return Response(status_code=response.status_code, content=content, media_type=content_type)
