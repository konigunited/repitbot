from typing import Optional

from ..core.config import get_settings
from .api_client import api_client

SETTINGS = get_settings()


async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    data = await api_client.get("/users/users", params={"telegram_id": telegram_id})
    if isinstance(data, list):
        for item in data:
            if str(item.get("telegram_id")) == str(telegram_id):
                return item
    return None


async def ensure_user_exists(telegram_id: int, username: str) -> dict:
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        return user
    payload = {
        "full_name": username or f"Student {telegram_id}",
        "email": f"auto_{telegram_id}@repitbot.local",
        "role": "student",
        "telegram_id": str(telegram_id),
    }
    created = await api_client.post("/users/users", json=payload)
    return created
