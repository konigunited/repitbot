from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from ...schemas import LessonCreate, LessonOut, LessonUpdate
from ...services.lesson_service import lesson_service

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "healthy"}


@router.post("/", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_lesson(payload: LessonCreate) -> LessonOut:
    lesson = lesson_service.create_lesson(payload)
    return LessonOut.model_validate(lesson)


@router.get("/", response_model=list[LessonOut])
def list_lessons(
    tutor_id: Optional[int] = Query(None, gt=0),
    student_id: Optional[int] = Query(None, gt=0),
) -> list[LessonOut]:
    lessons = lesson_service.list_lessons(tutor_id=tutor_id, student_id=student_id)
    return [LessonOut.model_validate(lesson) for lesson in lessons]


@router.get("/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: int) -> LessonOut:
    lesson = lesson_service.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return LessonOut.model_validate(lesson)


@router.put("/{lesson_id}", response_model=LessonOut)
def update_lesson(lesson_id: int, payload: LessonUpdate) -> LessonOut:
    lesson = lesson_service.update_lesson(lesson_id, payload)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return LessonOut.model_validate(lesson)


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(lesson_id: int) -> None:
    deleted = lesson_service.delete_lesson(lesson_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
