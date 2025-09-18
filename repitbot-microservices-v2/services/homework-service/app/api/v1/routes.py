from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from ...schemas import HomeworkCreate, HomeworkOut, HomeworkUpdate
from ...services.homework_service import homework_service

router = APIRouter(prefix="/homework", tags=["homework"])


@router.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "healthy"}


@router.post("/", response_model=HomeworkOut, status_code=status.HTTP_201_CREATED)
def create_homework(payload: HomeworkCreate) -> HomeworkOut:
    homework = homework_service.create_homework(payload)
    return HomeworkOut.model_validate(homework)


@router.get("/", response_model=list[HomeworkOut])
def list_homework(
    student_id: Optional[int] = Query(None, gt=0),
    tutor_id: Optional[int] = Query(None, gt=0),
    status: Optional[str] = Query(None),
) -> list[HomeworkOut]:
    homeworks = homework_service.list_homework(student_id=student_id, tutor_id=tutor_id, status=status)
    return [HomeworkOut.model_validate(hw) for hw in homeworks]


@router.get("/{homework_id}", response_model=HomeworkOut)
def get_homework(homework_id: int) -> HomeworkOut:
    homework = homework_service.get_homework(homework_id)
    if not homework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
    return HomeworkOut.model_validate(homework)


@router.put("/{homework_id}", response_model=HomeworkOut)
def update_homework(homework_id: int, payload: HomeworkUpdate) -> HomeworkOut:
    homework = homework_service.update_homework(homework_id, payload)
    if not homework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
    return HomeworkOut.model_validate(homework)


@router.delete("/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_homework(homework_id: int) -> None:
    deleted = homework_service.delete_homework(homework_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
