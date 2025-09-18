from typing import List, Optional

from sqlalchemy import select

from ..core.database import session_scope
from ..models import Homework
from ..schemas import HomeworkCreate, HomeworkUpdate


class HomeworkService:
    """Business logic for managing homework assignments."""

    def create_homework(self, payload: HomeworkCreate) -> Homework:
        with session_scope() as session:
            homework = Homework(**payload.model_dump())
            session.add(homework)
            session.flush()
            session.refresh(homework)
            return homework

    def get_homework(self, homework_id: int) -> Optional[Homework]:
        with session_scope() as session:
            return session.get(Homework, homework_id)

    def list_homework(
        self,
        student_id: Optional[int] = None,
        tutor_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Homework]:
        with session_scope() as session:
            stmt = select(Homework)
            if student_id:
                stmt = stmt.where(Homework.student_id == student_id)
            if tutor_id:
                stmt = stmt.where(Homework.tutor_id == tutor_id)
            if status:
                stmt = stmt.where(Homework.status == status)
            stmt = stmt.order_by(Homework.deadline.is_(None), Homework.deadline.asc())
            return list(session.scalars(stmt))

    def update_homework(self, homework_id: int, payload: HomeworkUpdate) -> Optional[Homework]:
        with session_scope() as session:
            homework = session.get(Homework, homework_id)
            if not homework:
                return None
            update_data = payload.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(homework, field, value)
            session.add(homework)
            session.flush()
            session.refresh(homework)
            return homework

    def delete_homework(self, homework_id: int) -> bool:
        with session_scope() as session:
            homework = session.get(Homework, homework_id)
            if not homework:
                return False
            session.delete(homework)
            return True


homework_service = HomeworkService()
