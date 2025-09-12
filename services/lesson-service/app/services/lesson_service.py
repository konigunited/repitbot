# -*- coding: utf-8 -*-
"""
Бизнес-логика для управления уроками.
Мигрированная логика из handlers/tutor.py с адаптацией под микросервисную архитектуру.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.lesson import (
    Lesson, Schedule, LessonAttendance, LessonCancellation,
    TopicMastery, AttendanceStatus, LessonStatus, ScheduleRecurrenceType
)
from ..schemas.lesson import (
    LessonCreate, LessonUpdate, LessonReschedule, LessonCancel,
    LessonFilter, ScheduleCreate, ScheduleUpdate, AttendanceCreate,
    LessonStats, StudentLessonStats
)
from ..database.connection import get_db_session
from ..events.lesson_events import LessonEventPublisher

logger = logging.getLogger(__name__)


class LessonService:
    """
    Сервис для управления уроками.
    Реализует бизнес-логику создания, редактирования, переноса и отмены уроков.
    """
    
    def __init__(self, event_publisher: Optional[LessonEventPublisher] = None):
        self.event_publisher = event_publisher
    
    async def create_lesson(
        self,
        lesson_data: LessonCreate,
        created_by: int,
        db: AsyncSession
    ) -> Lesson:
        """Создание нового урока."""
        try:
            # Создание урока
            lesson = Lesson(
                topic=lesson_data.topic,
                date=lesson_data.date,
                duration_minutes=lesson_data.duration_minutes,
                student_id=lesson_data.student_id,
                tutor_id=lesson_data.tutor_id,
                schedule_id=lesson_data.schedule_id,
                skills_developed=lesson_data.skills_developed,
                mastery_level=TopicMastery(lesson_data.mastery_level.value),
                mastery_comment=lesson_data.mastery_comment,
                notes=lesson_data.notes,
                room_url=lesson_data.room_url,
                created_by=created_by
            )
            
            db.add(lesson)
            await db.commit()
            await db.refresh(lesson)
            
            # Отправка события
            if self.event_publisher:
                await self.event_publisher.publish_lesson_created(lesson)
            
            logger.info(f"Created lesson {lesson.id} for student {lesson.student_id}")
            return lesson
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create lesson: {e}")
            raise
    
    async def get_lesson_by_id(self, lesson_id: int, db: AsyncSession) -> Optional[Lesson]:
        """Получение урока по ID."""
        result = await db.get(Lesson, lesson_id)
        return result
    
    async def update_lesson(
        self,
        lesson_id: int,
        lesson_data: LessonUpdate,
        updated_by: int,
        db: AsyncSession
    ) -> Optional[Lesson]:
        """Обновление урока."""
        try:
            lesson = await db.get(Lesson, lesson_id)
            if not lesson:
                return None
            
            # Сохранение старых значений для события
            old_data = {
                "topic": lesson.topic,
                "date": lesson.date,
                "mastery_level": lesson.mastery_level.value,
                "attendance_status": lesson.attendance_status.value,
                "lesson_status": lesson.lesson_status.value
            }
            
            # Обновление полей
            update_data = lesson_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(lesson, field):
                    if field in ['mastery_level', 'attendance_status', 'lesson_status']:
                        # Обработка enum полей
                        if field == 'mastery_level' and value:
                            setattr(lesson, field, TopicMastery(value.value))
                        elif field == 'attendance_status' and value:
                            setattr(lesson, field, AttendanceStatus(value.value))
                        elif field == 'lesson_status' and value:
                            setattr(lesson, field, LessonStatus(value.value))
                    else:
                        setattr(lesson, field, value)
            
            lesson.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(lesson)
            
            # Отправка события
            if self.event_publisher:
                await self.event_publisher.publish_lesson_updated(lesson, old_data)
            
            logger.info(f"Updated lesson {lesson.id}")
            return lesson
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update lesson {lesson_id}: {e}")
            raise
    
    async def reschedule_lesson(
        self,
        lesson_id: int,
        reschedule_data: LessonReschedule,
        rescheduled_by: int,
        db: AsyncSession
    ) -> Optional[Lesson]:
        """
        Перенос урока на новую дату.
        Сохраняет оригинальную дату и реализует логику сдвига будущих уроков.
        """
        try:
            lesson = await db.get(Lesson, lesson_id)
            if not lesson:
                return None
            
            original_date = lesson.date
            
            # Обновление урока
            lesson.original_date = original_date
            lesson.date = reschedule_data.new_date
            lesson.is_rescheduled = True
            lesson.reschedule_reason = reschedule_data.reason
            lesson.attendance_status = AttendanceStatus.RESCHEDULED
            lesson.updated_at = datetime.now()
            
            # Создание записи о переносе
            cancellation = LessonCancellation(
                lesson_id=lesson.id,
                action_type="rescheduled",
                original_date=original_date,
                new_date=reschedule_data.new_date,
                reason=reschedule_data.reason,
                initiated_by=rescheduled_by
            )
            db.add(cancellation)
            
            await db.commit()
            await db.refresh(lesson)
            
            # Отправка события
            if self.event_publisher:
                await self.event_publisher.publish_lesson_rescheduled(
                    lesson, original_date, reschedule_data.new_date, reschedule_data.reason
                )
            
            logger.info(f"Rescheduled lesson {lesson.id} from {original_date} to {reschedule_data.new_date}")
            return lesson
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to reschedule lesson {lesson_id}: {e}")
            raise
    
    async def cancel_lesson(
        self,
        lesson_id: int,
        cancel_data: LessonCancel,
        cancelled_by: int,
        db: AsyncSession
    ) -> Optional[Lesson]:
        """
        Отмена урока с реализацией логики сдвига будущих уроков.
        Мигрированная логика из shift_lessons_after_cancellation.
        """
        try:
            lesson = await db.get(Lesson, lesson_id)
            if not lesson:
                return None
            
            original_date = lesson.date
            
            # Обновление статуса урока
            lesson.attendance_status = AttendanceStatus(cancel_data.attendance_status.value)
            lesson.lesson_status = LessonStatus.NOT_CONDUCTED
            lesson.updated_at = datetime.now()
            
            # Создание записи об отмене
            cancellation = LessonCancellation(
                lesson_id=lesson.id,
                action_type="cancelled",
                original_date=original_date,
                reason=cancel_data.reason,
                initiated_by=cancelled_by
            )
            db.add(cancellation)
            
            # Логика сдвига будущих уроков (из shift_lessons_after_cancellation)
            await self._shift_lessons_after_cancellation(lesson, db)
            
            await db.commit()
            await db.refresh(lesson)
            
            # Отправка события
            if self.event_publisher:
                await self.event_publisher.publish_lesson_cancelled(lesson, cancel_data.reason)
            
            logger.info(f"Cancelled lesson {lesson.id}")
            return lesson
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to cancel lesson {lesson_id}: {e}")
            raise
    
    async def _shift_lessons_after_cancellation(self, cancelled_lesson: Lesson, db: AsyncSession):
        """
        Реализация логики сдвига уроков при отмене.
        Мигрировано из database.py -> shift_lessons_after_cancellation.
        """
        try:
            # Получаем все будущие уроки этого ученика
            from sqlalchemy import select
            
            stmt = select(Lesson).where(
                and_(
                    Lesson.student_id == cancelled_lesson.student_id,
                    Lesson.date >= cancelled_lesson.date
                )
            ).order_by(Lesson.date.asc())
            
            result = await db.execute(stmt)
            all_lessons = result.scalars().all()
            
            if len(all_lessons) <= 1:
                # Если это последний урок, создаем урок для отработки
                far_future_date = datetime.now() + timedelta(days=3650)  # 10 лет вперед
                
                makeup_lesson = Lesson(
                    student_id=cancelled_lesson.student_id,
                    tutor_id=cancelled_lesson.tutor_id,
                    topic=cancelled_lesson.topic,
                    date=far_future_date,
                    duration_minutes=cancelled_lesson.duration_minutes,
                    attendance_status=AttendanceStatus.ATTENDED,
                    mastery_level=TopicMastery.NOT_LEARNED,
                    created_by=cancelled_lesson.created_by
                )
                db.add(makeup_lesson)
                logger.info(f"Created makeup lesson for cancelled lesson {cancelled_lesson.id}")
                return
            
            # Сохраняем даты
            dates = [lesson.date for lesson in all_lessons]
            
            # Отмененный урок встает на место следующего урока
            all_lessons[0].date = dates[1]
            
            # Все остальные уроки сдвигаются на +1 дату
            for i in range(1, len(all_lessons) - 1):
                all_lessons[i].date = dates[i + 1]
            
            # Последний урок лишается даты - создаем для него урок-заглушку
            last_lesson = all_lessons[-1]
            last_topic = last_lesson.topic
            
            # Удаляем последний урок из расписания
            await db.delete(last_lesson)
            
            # Создаем урок-заглушку для последнего урока
            far_future_date = datetime.now() + timedelta(days=3650)
            
            makeup_lesson = Lesson(
                student_id=cancelled_lesson.student_id,
                tutor_id=cancelled_lesson.tutor_id,
                topic=last_topic,
                date=far_future_date,
                duration_minutes=last_lesson.duration_minutes,
                attendance_status=AttendanceStatus.ATTENDED,
                mastery_level=TopicMastery.NOT_LEARNED,
                created_by=last_lesson.created_by
            )
            db.add(makeup_lesson)
            
            logger.info(f"Shifted {len(all_lessons)} lessons after cancellation")
            
        except Exception as e:
            logger.error(f"Failed to shift lessons after cancellation: {e}")
            raise
    
    async def get_lessons(
        self,
        filters: LessonFilter,
        db: AsyncSession
    ) -> tuple[List[Lesson], int]:
        """Получение списка уроков с фильтрацией и пагинацией."""
        try:
            from sqlalchemy import select
            
            # Базовый запрос
            stmt = select(Lesson)
            count_stmt = select(func.count(Lesson.id))
            
            # Применение фильтров
            conditions = []
            
            if filters.student_id:
                conditions.append(Lesson.student_id == filters.student_id)
            
            if filters.tutor_id:
                conditions.append(Lesson.tutor_id == filters.tutor_id)
            
            if filters.date_from:
                conditions.append(Lesson.date >= filters.date_from)
            
            if filters.date_to:
                conditions.append(Lesson.date <= filters.date_to)
            
            if filters.lesson_status:
                conditions.append(Lesson.lesson_status == LessonStatus(filters.lesson_status.value))
            
            if filters.attendance_status:
                conditions.append(Lesson.attendance_status == AttendanceStatus(filters.attendance_status.value))
            
            if filters.mastery_level:
                conditions.append(Lesson.mastery_level == TopicMastery(filters.mastery_level.value))
            
            if filters.topic_search:
                conditions.append(Lesson.topic.ilike(f"%{filters.topic_search}%"))
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
                count_stmt = count_stmt.where(and_(*conditions))
            
            # Подсчет общего количества
            count_result = await db.execute(count_stmt)
            total = count_result.scalar()
            
            # Сортировка
            order_column = getattr(Lesson, filters.sort_by)
            if filters.sort_order == "desc":
                stmt = stmt.order_by(desc(order_column))
            else:
                stmt = stmt.order_by(asc(order_column))
            
            # Пагинация
            offset = (filters.page - 1) * filters.page_size
            stmt = stmt.offset(offset).limit(filters.page_size)
            
            # Выполнение запроса
            result = await db.execute(stmt)
            lessons = result.scalars().all()
            
            return lessons, total
            
        except Exception as e:
            logger.error(f"Failed to get lessons: {e}")
            raise
    
    async def mark_attendance(
        self,
        lesson_id: int,
        attendance_data: AttendanceCreate,
        recorded_by: int,
        db: AsyncSession
    ) -> Optional[LessonAttendance]:
        """Отметка посещаемости урока."""
        try:
            # Получение урока
            lesson = await db.get(Lesson, lesson_id)
            if not lesson:
                return None
            
            # Обновление основного статуса в уроке
            lesson.attendance_status = AttendanceStatus(attendance_data.attendance_status.value)
            lesson.is_attended = attendance_data.attendance_status == AttendanceStatusSchema.ATTENDED
            lesson.lesson_status = LessonStatus.CONDUCTED
            lesson.updated_at = datetime.now()
            
            # Создание детальной записи о посещаемости
            attendance = LessonAttendance(
                lesson_id=lesson.id,
                attendance_status=AttendanceStatus(attendance_data.attendance_status.value),
                check_in_time=attendance_data.check_in_time,
                check_out_time=attendance_data.check_out_time,
                absence_reason=attendance_data.absence_reason,
                is_excused=attendance_data.is_excused,
                student_rating=attendance_data.student_rating,
                student_feedback=attendance_data.student_feedback,
                tutor_rating=attendance_data.tutor_rating,
                tutor_notes=attendance_data.tutor_notes,
                recorded_by=recorded_by
            )
            
            # Расчет фактической длительности
            if attendance_data.check_in_time and attendance_data.check_out_time:
                duration = attendance_data.check_out_time - attendance_data.check_in_time
                attendance.actual_duration_minutes = int(duration.total_seconds() / 60)
            
            db.add(attendance)
            await db.commit()
            await db.refresh(attendance)
            
            # Отправка события
            if self.event_publisher:
                await self.event_publisher.publish_attendance_marked(lesson, attendance)
            
            logger.info(f"Marked attendance for lesson {lesson.id}")
            return attendance
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to mark attendance for lesson {lesson_id}: {e}")
            raise
    
    async def get_lesson_stats(
        self,
        student_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> LessonStats:
        """Получение статистики по урокам."""
        try:
            from sqlalchemy import select, case
            
            # Базовые условия
            conditions = []
            if student_id:
                conditions.append(Lesson.student_id == student_id)
            if date_from:
                conditions.append(Lesson.date >= date_from)
            if date_to:
                conditions.append(Lesson.date <= date_to)
            
            # Общая статистика
            total_stmt = select(func.count(Lesson.id))
            conducted_stmt = select(func.count(Lesson.id)).where(
                Lesson.lesson_status == LessonStatus.CONDUCTED
            )
            cancelled_stmt = select(func.count(Lesson.id)).where(
                Lesson.attendance_status.in_([
                    AttendanceStatus.EXCUSED_ABSENCE,
                    AttendanceStatus.UNEXCUSED_ABSENCE
                ])
            )
            rescheduled_stmt = select(func.count(Lesson.id)).where(
                Lesson.is_rescheduled == True
            )
            
            # Применение условий
            if conditions:
                condition = and_(*conditions)
                total_stmt = total_stmt.where(condition)
                conducted_stmt = conducted_stmt.where(condition)
                cancelled_stmt = cancelled_stmt.where(condition)
                rescheduled_stmt = rescheduled_stmt.where(condition)
            
            # Выполнение запросов
            total_result = await db.execute(total_stmt)
            conducted_result = await db.execute(conducted_stmt)
            cancelled_result = await db.execute(cancelled_stmt)
            rescheduled_result = await db.execute(rescheduled_stmt)
            
            total_lessons = total_result.scalar()
            conducted_lessons = conducted_result.scalar()
            cancelled_lessons = cancelled_result.scalar()
            rescheduled_lessons = rescheduled_result.scalar()
            
            # Средняя длительность
            avg_duration_stmt = select(func.avg(Lesson.duration_minutes))
            if conditions:
                avg_duration_stmt = avg_duration_stmt.where(and_(*conditions))
            
            avg_duration_result = await db.execute(avg_duration_stmt)
            average_duration = avg_duration_result.scalar() or 0
            
            # Процент посещаемости
            attendance_rate = (conducted_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            # Распределение уровней освоения
            mastery_stmt = select(
                Lesson.mastery_level,
                func.count(Lesson.id)
            ).group_by(Lesson.mastery_level)
            
            if conditions:
                mastery_stmt = mastery_stmt.where(and_(*conditions))
            
            mastery_result = await db.execute(mastery_stmt)
            mastery_distribution = {
                row[0].value: row[1] for row in mastery_result.fetchall()
            }
            
            return LessonStats(
                total_lessons=total_lessons,
                conducted_lessons=conducted_lessons,
                cancelled_lessons=cancelled_lessons,
                rescheduled_lessons=rescheduled_lessons,
                average_duration=average_duration,
                attendance_rate=attendance_rate,
                mastery_distribution=mastery_distribution
            )
            
        except Exception as e:
            logger.error(f"Failed to get lesson stats: {e}")
            raise
    
    async def delete_lesson(self, lesson_id: int, db: AsyncSession) -> bool:
        """Удаление урока."""
        try:
            lesson = await db.get(Lesson, lesson_id)
            if not lesson:
                return False
            
            await db.delete(lesson)
            await db.commit()
            
            # Отправка события
            if self.event_publisher:
                await self.event_publisher.publish_lesson_deleted(lesson)
            
            logger.info(f"Deleted lesson {lesson.id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete lesson {lesson_id}: {e}")
            raise