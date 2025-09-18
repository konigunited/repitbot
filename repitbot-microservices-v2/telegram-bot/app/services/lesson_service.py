from typing import List

from .api_client import api_client


async def get_upcoming_lessons(student_id: int) -> List[dict]:
    data = await api_client.get("/lessons/lessons", params={"student_id": student_id})
    return data
