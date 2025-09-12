# -*- coding: utf-8 -*-
"""
Progress Service
Сервис отслеживания прогресса обучения
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, asc
from ..database.connection import get_db_session
from ..models.student import Student
from ..models.progress import (
    LearningProgress, SubjectProgress, LessonProgress,
    SkillProgress, StudySession, ProgressSnapshot
)
from ..schemas.progress import ProgressUpdateCreate

logger = logging.getLogger(__name__)

class ProgressService:
    """Сервис отслеживания прогресса обучения"""
    
    # Весовые коэффициенты для расчета общего прогресса
    PROGRESS_WEIGHTS = {
        "lesson_completion": 0.4,      # Завершение уроков
        "homework_quality": 0.3,       # Качество домашних заданий
        "consistency": 0.2,            # Регулярность занятий
        "engagement": 0.1              # Вовлеченность (активность)
    }
    
    # Конфигурация навыков
    SKILL_CATEGORIES = {
        "grammar": {
            "name": "Грамматика",
            "description": "Знание грамматических правил",
            "icon": "📚",
            "max_level": 100
        },
        "vocabulary": {
            "name": "Словарь",
            "description": "Объем словарного запаса",
            "icon": "📝",
            "max_level": 100
        },
        "speaking": {
            "name": "Говорение",
            "description": "Навыки устной речи",
            "icon": "🗣️",
            "max_level": 100
        },
        "listening": {
            "name": "Аудирование",
            "description": "Понимание речи на слух",
            "icon": "👂",
            "max_level": 100
        },
        "reading": {
            "name": "Чтение",
            "description": "Понимание письменного текста",
            "icon": "📖",
            "max_level": 100
        },
        "writing": {
            "name": "Письмо",
            "description": "Навыки письменной речи",
            "icon": "✍️",
            "max_level": 100
        }
    }
    
    async def update_lesson_progress(
        self,
        student_id: int,
        lesson_id: int,
        completion_rate: float,
        time_spent: int,
        correct_answers: int,
        total_questions: int,
        skills_practiced: List[str] = None
    ) -> Dict[str, Any]:
        """Обновление прогресса по уроку"""
        try:
            async with get_db_session() as session:
                # Получаем или создаем запись о прогрессе урока
                lesson_progress = await session.get(LessonProgress, (student_id, lesson_id))
                
                if not lesson_progress:
                    lesson_progress = LessonProgress(
                        student_id=student_id,
                        lesson_id=lesson_id,
                        completion_rate=0.0,
                        time_spent=0,
                        attempts=0,
                        best_score=0.0,
                        last_accessed=datetime.utcnow()
                    )
                    session.add(lesson_progress)
                
                # Обновляем данные
                lesson_progress.completion_rate = max(lesson_progress.completion_rate, completion_rate)
                lesson_progress.time_spent += time_spent
                lesson_progress.attempts += 1
                lesson_progress.last_accessed = datetime.utcnow()
                
                # Рассчитываем текущий результат
                current_score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
                lesson_progress.best_score = max(lesson_progress.best_score, current_score)
                
                # Урок считается завершенным, если прогресс >= 90%
                if completion_rate >= 0.9:
                    lesson_progress.completed_at = datetime.utcnow()
                
                # Обновляем навыки
                if skills_practiced:
                    await self._update_skills_progress(
                        session, student_id, skills_practiced, 
                        current_score, time_spent
                    )
                
                # Создаем сессию обучения
                study_session = StudySession(
                    student_id=student_id,
                    lesson_id=lesson_id,
                    duration=time_spent,
                    score=current_score,
                    completed=completion_rate >= 0.9,
                    skills_practiced=skills_practiced or []
                )
                session.add(study_session)
                
                await session.commit()
                
                # Обновляем общий прогресс
                await self._recalculate_overall_progress(student_id)
                
                return {
                    "success": True,
                    "lesson_id": lesson_id,
                    "completion_rate": lesson_progress.completion_rate,
                    "best_score": lesson_progress.best_score,
                    "attempts": lesson_progress.attempts,
                    "current_score": current_score,
                    "completed": completion_rate >= 0.9
                }
                
        except Exception as e:
            logger.error(f"Error updating lesson progress: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_student_progress(self, student_id: int) -> Dict[str, Any]:
        """Получение полного прогресса студента"""
        try:
            async with get_db_session() as session:
                # Получаем общий прогресс
                learning_progress = await session.execute(
                    select(LearningProgress)
                    .options(selectinload(LearningProgress.subject_progresses))
                    .where(LearningProgress.student_id == student_id)
                )
                progress = learning_progress.scalar_one_or_none()
                
                if not progress:
                    # Создаем если не существует
                    progress = await self._initialize_student_progress(session, student_id)
                
                # Получаем прогресс по навыкам
                skills_result = await session.execute(
                    select(SkillProgress).where(SkillProgress.student_id == student_id)
                )
                skills = skills_result.scalars().all()
                
                # Получаем недавние сессии
                recent_sessions = await session.execute(
                    select(StudySession)
                    .where(
                        and_(
                            StudySession.student_id == student_id,
                            StudySession.created_at >= datetime.utcnow() - timedelta(days=30)
                        )
                    )
                    .order_by(desc(StudySession.created_at))
                    .limit(10)
                )
                sessions = recent_sessions.scalars().all()
                
                # Статистика активности
                activity_stats = await self._calculate_activity_stats(session, student_id)
                
                return {
                    "student_id": student_id,
                    "overall_progress": {
                        "completion_rate": float(progress.overall_completion),
                        "lessons_completed": progress.lessons_completed,
                        "total_lessons": progress.total_lessons,
                        "average_score": float(progress.average_score or 0),
                        "total_time_spent": progress.total_time_spent,
                        "streak_days": progress.current_streak,
                        "last_activity": progress.last_activity
                    },
                    "subjects": [
                        {
                            "subject_id": sp.subject_id,
                            "completion_rate": float(sp.completion_rate),
                            "lessons_completed": sp.lessons_completed,
                            "total_lessons": sp.total_lessons,
                            "average_score": float(sp.average_score or 0),
                            "last_lesson_date": sp.last_lesson_date
                        }
                        for sp in progress.subject_progresses
                    ],
                    "skills": [
                        {
                            "skill_name": skill.skill_name,
                            "level": skill.current_level,
                            "progress": float(skill.progress_percent),
                            "practice_count": skill.practice_count,
                            "last_practiced": skill.last_practiced
                        }
                        for skill in skills
                    ],
                    "recent_sessions": [
                        {
                            "lesson_id": session.lesson_id,
                            "date": session.created_at,
                            "duration": session.duration,
                            "score": float(session.score),
                            "completed": session.completed,
                            "skills_practiced": session.skills_practiced
                        }
                        for session in sessions
                    ],
                    "activity_stats": activity_stats
                }
                
        except Exception as e:
            logger.error(f"Error getting student progress: {e}")
            return {"error": str(e)}
    
    async def get_progress_analytics(self, student_id: int, period: str = "month") -> Dict[str, Any]:
        """Получение аналитики прогресса"""
        try:
            async with get_db_session() as session:
                # Определяем период
                if period == "week":
                    start_date = datetime.utcnow() - timedelta(days=7)
                elif period == "month":
                    start_date = datetime.utcnow() - timedelta(days=30)
                elif period == "quarter":
                    start_date = datetime.utcnow() - timedelta(days=90)
                else:
                    start_date = datetime.utcnow() - timedelta(days=365)
                
                # Получаем снимки прогресса за период
                snapshots_result = await session.execute(
                    select(ProgressSnapshot)
                    .where(
                        and_(
                            ProgressSnapshot.student_id == student_id,
                            ProgressSnapshot.created_at >= start_date
                        )
                    )
                    .order_by(asc(ProgressSnapshot.created_at))
                )
                snapshots = snapshots_result.scalars().all()
                
                # Получаем сессии за период
                sessions_result = await session.execute(
                    select(StudySession)
                    .where(
                        and_(
                            StudySession.student_id == student_id,
                            StudySession.created_at >= start_date
                        )
                    )
                    .order_by(asc(StudySession.created_at))
                )
                sessions = sessions_result.scalars().all()
                
                # Анализируем тренды
                progress_trend = self._analyze_progress_trend(snapshots)
                activity_pattern = self._analyze_activity_pattern(sessions)
                performance_metrics = self._calculate_performance_metrics(sessions)
                
                return {
                    "period": period,
                    "start_date": start_date,
                    "end_date": datetime.utcnow(),
                    "progress_trend": progress_trend,
                    "activity_pattern": activity_pattern,
                    "performance_metrics": performance_metrics,
                    "recommendations": await self._generate_recommendations(
                        student_id, sessions, snapshots
                    )
                }
                
        except Exception as e:
            logger.error(f"Error getting progress analytics: {e}")
            return {"error": str(e)}
    
    async def create_progress_snapshot(self, student_id: int) -> bool:
        """Создание снимка текущего прогресса"""
        try:
            async with get_db_session() as session:
                progress = await session.execute(
                    select(LearningProgress).where(LearningProgress.student_id == student_id)
                )
                current_progress = progress.scalar_one_or_none()
                
                if not current_progress:
                    return False
                
                # Создаем снимок
                snapshot = ProgressSnapshot(
                    student_id=student_id,
                    overall_completion=current_progress.overall_completion,
                    lessons_completed=current_progress.lessons_completed,
                    average_score=current_progress.average_score,
                    total_time_spent=current_progress.total_time_spent,
                    streak_days=current_progress.current_streak,
                    metadata={
                        "snapshot_reason": "daily_snapshot",
                        "total_lessons": current_progress.total_lessons
                    }
                )
                session.add(snapshot)
                await session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Error creating progress snapshot: {e}")
            return False
    
    async def _update_skills_progress(
        self, 
        session: AsyncSession,
        student_id: int,
        skills: List[str],
        score: float,
        time_spent: int
    ):
        """Обновление прогресса по навыкам"""
        for skill_name in skills:
            if skill_name not in self.SKILL_CATEGORIES:
                continue
            
            # Получаем или создаем запись о навыке
            skill_progress = await session.execute(
                select(SkillProgress).where(
                    and_(
                        SkillProgress.student_id == student_id,
                        SkillProgress.skill_name == skill_name
                    )
                )
            )
            skill = skill_progress.scalar_one_or_none()
            
            if not skill:
                skill = SkillProgress(
                    student_id=student_id,
                    skill_name=skill_name,
                    current_level=1,
                    progress_percent=0.0,
                    practice_count=0,
                    last_practiced=datetime.utcnow()
                )
                session.add(skill)
            
            # Обновляем прогресс
            skill.practice_count += 1
            skill.last_practiced = datetime.utcnow()
            
            # Прогресс основан на результате и времени практики
            progress_gain = (score / 100) * (time_spent / 60) * 0.5  # 0.5% за минуту при 100% результате
            skill.progress_percent = min(100.0, skill.progress_percent + progress_gain)
            
            # Обновляем уровень (каждые 10% - новый уровень)
            new_level = min(10, int(skill.progress_percent // 10) + 1)
            skill.current_level = new_level
    
    async def _recalculate_overall_progress(self, student_id: int):
        """Пересчет общего прогресса студента"""
        try:
            async with get_db_session() as session:
                # Получаем все уроки студента
                lesson_progresses = await session.execute(
                    select(LessonProgress).where(LessonProgress.student_id == student_id)
                )
                lessons = lesson_progresses.scalars().all()
                
                if not lessons:
                    return
                
                # Рассчитываем метрики
                total_lessons = len(lessons)
                completed_lessons = len([l for l in lessons if l.completed_at])
                total_time = sum(l.time_spent for l in lessons)
                average_score = sum(l.best_score for l in lessons) / total_lessons if lessons else 0
                
                # Получаем или создаем общий прогресс
                learning_progress = await session.execute(
                    select(LearningProgress).where(LearningProgress.student_id == student_id)
                )
                progress = learning_progress.scalar_one_or_none()
                
                if not progress:
                    progress = await self._initialize_student_progress(session, student_id)
                
                # Обновляем данные
                progress.total_lessons = total_lessons
                progress.lessons_completed = completed_lessons
                progress.overall_completion = Decimal(completed_lessons / total_lessons * 100) if total_lessons > 0 else Decimal(0)
                progress.total_time_spent = total_time
                progress.average_score = Decimal(average_score)
                progress.last_activity = datetime.utcnow()
                
                # Рассчитываем серию
                progress.current_streak = await self._calculate_current_streak(session, student_id)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error recalculating overall progress: {e}")
    
    async def _initialize_student_progress(self, session: AsyncSession, student_id: int) -> LearningProgress:
        """Инициализация прогресса для нового студента"""
        progress = LearningProgress(
            student_id=student_id,
            overall_completion=Decimal(0),
            lessons_completed=0,
            total_lessons=0,
            average_score=Decimal(0),
            total_time_spent=0,
            current_streak=0,
            longest_streak=0,
            last_activity=datetime.utcnow()
        )
        session.add(progress)
        return progress
    
    async def _calculate_current_streak(self, session: AsyncSession, student_id: int) -> int:
        """Вычисление текущей серии активности"""
        # Получаем последние сессии
        recent_sessions = await session.execute(
            select(StudySession)
            .where(StudySession.student_id == student_id)
            .order_by(desc(StudySession.created_at))
            .limit(30)
        )
        sessions = recent_sessions.scalars().all()
        
        if not sessions:
            return 0
        
        # Группируем по дням
        activity_days = set()
        for session in sessions:
            activity_days.add(session.created_at.date())
        
        # Считаем серию с сегодняшнего дня
        current_date = datetime.utcnow().date()
        streak = 0
        
        while current_date in activity_days:
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak
    
    async def _calculate_activity_stats(self, session: AsyncSession, student_id: int) -> Dict[str, Any]:
        """Вычисление статистики активности"""
        # Последние 30 дней
        month_ago = datetime.utcnow() - timedelta(days=30)
        
        sessions = await session.execute(
            select(StudySession)
            .where(
                and_(
                    StudySession.student_id == student_id,
                    StudySession.created_at >= month_ago
                )
            )
        )
        recent_sessions = sessions.scalars().all()
        
        total_sessions = len(recent_sessions)
        total_time = sum(s.duration for s in recent_sessions)
        average_session_time = total_time / total_sessions if total_sessions > 0 else 0
        completion_rate = len([s for s in recent_sessions if s.completed]) / total_sessions * 100 if total_sessions > 0 else 0
        
        # Активные дни
        active_days = len(set(s.created_at.date() for s in recent_sessions))
        
        return {
            "total_sessions_month": total_sessions,
            "total_time_month": total_time,
            "average_session_time": average_session_time,
            "completion_rate": completion_rate,
            "active_days_month": active_days,
            "sessions_per_week": total_sessions / 4.3 if total_sessions > 0 else 0
        }
    
    def _analyze_progress_trend(self, snapshots: List[ProgressSnapshot]) -> Dict[str, Any]:
        """Анализ тренда прогресса"""
        if len(snapshots) < 2:
            return {"trend": "insufficient_data", "change": 0}
        
        first_snapshot = snapshots[0]
        last_snapshot = snapshots[-1]
        
        progress_change = float(last_snapshot.overall_completion - first_snapshot.overall_completion)
        score_change = float((last_snapshot.average_score or 0) - (first_snapshot.average_score or 0))
        
        if progress_change > 5:
            trend = "improving"
        elif progress_change < -2:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "progress_change": progress_change,
            "score_change": score_change,
            "data_points": len(snapshots)
        }
    
    def _analyze_activity_pattern(self, sessions: List[StudySession]) -> Dict[str, Any]:
        """Анализ паттерна активности"""
        if not sessions:
            return {"pattern": "no_activity", "consistency": 0}
        
        # Группируем по дням недели
        weekday_activity = [0] * 7
        for session in sessions:
            weekday = session.created_at.weekday()
            weekday_activity[weekday] += 1
        
        # Группируем по часам дня
        hour_activity = [0] * 24
        for session in sessions:
            hour = session.created_at.hour
            hour_activity[hour] += 1
        
        # Находим наиболее активные периоды
        most_active_weekday = weekday_activity.index(max(weekday_activity))
        most_active_hour = hour_activity.index(max(hour_activity))
        
        # Вычисляем консистентность (стандартное отклонение активности по дням)
        import statistics
        consistency = 100 - (statistics.stdev(weekday_activity) / max(weekday_activity) * 100) if max(weekday_activity) > 0 else 0
        
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        return {
            "pattern": "consistent" if consistency > 70 else "irregular",
            "consistency": consistency,
            "most_active_weekday": weekdays[most_active_weekday],
            "most_active_hour": most_active_hour,
            "total_sessions": len(sessions)
        }
    
    def _calculate_performance_metrics(self, sessions: List[StudySession]) -> Dict[str, Any]:
        """Вычисление метрик производительности"""
        if not sessions:
            return {}
        
        scores = [float(s.score) for s in sessions if s.score is not None]
        durations = [s.duration for s in sessions]
        completed_sessions = [s for s in sessions if s.completed]
        
        return {
            "average_score": sum(scores) / len(scores) if scores else 0,
            "score_improvement": (scores[-1] - scores[0]) if len(scores) > 1 else 0,
            "average_duration": sum(durations) / len(durations) if durations else 0,
            "completion_rate": len(completed_sessions) / len(sessions) * 100,
            "total_study_time": sum(durations),
            "session_count": len(sessions)
        }
    
    async def _generate_recommendations(
        self,
        student_id: int,
        sessions: List[StudySession],
        snapshots: List[ProgressSnapshot]
    ) -> List[str]:
        """Генерация рекомендаций на основе анализа прогресса"""
        recommendations = []
        
        if not sessions:
            recommendations.append("Начните с регулярных занятий - хотя бы 15 минут в день")
            return recommendations
        
        # Анализируем активность
        recent_sessions = [s for s in sessions if s.created_at >= datetime.utcnow() - timedelta(days=7)]
        
        if len(recent_sessions) < 3:
            recommendations.append("Увеличьте частоту занятий - занимайтесь как минимум 3 раза в неделю")
        
        # Анализируем продолжительность
        avg_duration = sum(s.duration for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0
        if avg_duration < 15:
            recommendations.append("Увеличьте продолжительность занятий до 20-30 минут для лучших результатов")
        
        # Анализируем качество
        recent_scores = [s.score for s in recent_sessions if s.score is not None]
        if recent_scores and sum(recent_scores) / len(recent_scores) < 70:
            recommendations.append("Повторите предыдущие материалы перед изучением новых")
        
        # Анализируем завершение
        completion_rate = len([s for s in recent_sessions if s.completed]) / len(recent_sessions) * 100 if recent_sessions else 0
        if completion_rate < 80:
            recommendations.append("Старайтесь завершать начатые уроки до конца")
        
        return recommendations