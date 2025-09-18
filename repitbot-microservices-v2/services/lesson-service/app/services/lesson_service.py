from typing import List, Optional

from sqlalchemy import select

from ..core.database import session_scope
from ..models import Lesson
from ..schemas import LessonCreate, LessonUpdate


class LessonService:
    """Business logic for managing lessons."""

    def create_lesson(self, payload: LessonCreate) -> Lesson:
        with session_scope() as session:
            lesson = Lesson(**payload.model_dump())
            session.add(lesson)
            session.flush()
            session.refresh(lesson)
            return lesson

    def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        with session_scope() as session:
            return session.get(Lesson, lesson_id)

    def list_lessons(self, tutor_id: Optional[int] = None, student_id: Optional[int] = None) -> List[Lesson]:
        with session_scope() as session:
            stmt = select(Lesson)
            if tutor_id:
                stmt = stmt.where(Lesson.tutor_id == tutor_id)
            if student_id:
                stmt = stmt.where(Lesson.student_id == student_id)
            stmt = stmt.order_by(Lesson.scheduled_at.desc())
            return list(session.scalars(stmt))

    def update_lesson(self, lesson_id: int, payload: LessonUpdate) -> Optional[Lesson]:
        with session_scope() as session:
            lesson = session.get(Lesson, lesson_id)
            if not lesson:
                return None
            update_data = payload.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(lesson, field, value)
            session.add(lesson)
            session.flush()
            session.refresh(lesson)
            return lesson

    def delete_lesson(self, lesson_id: int) -> bool:
        with session_scope() as session:
            lesson = session.get(Lesson, lesson_id)
            if not lesson:
                return False
            session.delete(lesson)
            return True


lesson_service = LessonService()
