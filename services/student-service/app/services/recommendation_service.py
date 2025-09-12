# -*- coding: utf-8 -*-
"""
Recommendation Service
Сервис рекомендаций и персонализации обучения
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from ..database.connection import get_db_session
from ..models.student import Student
from ..models.progress import LearningProgress, SkillProgress, StudySession, LessonProgress
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

class RecommendationService:
    """Сервис рекомендаций и персонализации обучения"""
    
    # Типы рекомендаций
    RECOMMENDATION_TYPES = {
        "next_lesson": "Следующий урок",
        "review_material": "Повторение материала", 
        "skill_improvement": "Улучшение навыка",
        "difficulty_adjustment": "Корректировка сложности",
        "study_schedule": "Расписание занятий",
        "material_type": "Тип материалов"
    }
    
    # Факторы для рекомендаций
    RECOMMENDATION_FACTORS = {
        "performance": 0.3,      # Производительность
        "preferences": 0.2,      # Предпочтения
        "progress": 0.25,        # Прогресс
        "similarity": 0.15,      # Схожесть с другими
        "recency": 0.1          # Свежесть материала
    }
    
    async def get_personalized_recommendations(
        self,
        student_id: int,
        recommendation_type: str = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Получение персонализированных рекомендаций"""
        try:
            async with get_db_session() as session:
                # Получаем профиль студента
                student_profile = await self._build_student_profile(session, student_id)
                
                recommendations = []
                
                if recommendation_type in ["all", "next_lesson"]:
                    next_lessons = await self._recommend_next_lessons(session, student_profile)
                    recommendations.extend(next_lessons)
                
                if recommendation_type in ["all", "review_material"]:
                    review_materials = await self._recommend_review_materials(session, student_profile)
                    recommendations.extend(review_materials)
                
                if recommendation_type in ["all", "skill_improvement"]:
                    skill_improvements = await self._recommend_skill_improvements(session, student_profile)
                    recommendations.extend(skill_improvements)
                
                if recommendation_type in ["all", "study_schedule"]:
                    schedule_recommendations = await self._recommend_study_schedule(session, student_profile)
                    recommendations.extend(schedule_recommendations)
                
                if recommendation_type in ["all", "material_type"]:
                    material_types = await self._recommend_material_types(session, student_profile)
                    recommendations.extend(material_types)
                
                # Сортируем по релевантности и ограничиваем количество
                recommendations.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                return recommendations[:limit]
                
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    async def get_adaptive_difficulty(self, student_id: int, subject_id: int) -> Dict[str, Any]:
        """Получение адаптивного уровня сложности"""
        try:
            async with get_db_session() as session:
                # Получаем последние результаты студента
                recent_sessions = await session.execute(
                    select(StudySession)
                    .join(LessonProgress, StudySession.lesson_id == LessonProgress.lesson_id)
                    .where(
                        and_(
                            StudySession.student_id == student_id,
                            StudySession.created_at >= datetime.utcnow() - timedelta(days=14)
                        )
                    )
                    .order_by(desc(StudySession.created_at))
                    .limit(10)
                )
                sessions = recent_sessions.scalars().all()
                
                if not sessions:
                    return {"difficulty": "beginner", "confidence": 0.5}
                
                # Анализируем производительность
                scores = [s.score for s in sessions if s.score is not None]
                completion_rates = [1.0 if s.completed else 0.0 for s in sessions]
                
                avg_score = sum(scores) / len(scores) if scores else 0
                completion_rate = sum(completion_rates) / len(completion_rates)
                
                # Определяем уровень сложности
                performance_score = (avg_score * 0.7) + (completion_rate * 100 * 0.3)
                
                if performance_score >= 85:
                    difficulty = "advanced"
                    confidence = 0.9
                elif performance_score >= 70:
                    difficulty = "intermediate" 
                    confidence = 0.8
                elif performance_score >= 50:
                    difficulty = "beginner"
                    confidence = 0.7
                else:
                    difficulty = "remedial"
                    confidence = 0.6
                
                # Учитываем тренд
                if len(scores) >= 3:
                    recent_trend = np.polyfit(range(len(scores)), scores, 1)[0]
                    if recent_trend > 0:  # Улучшается
                        if difficulty == "beginner":
                            difficulty = "intermediate"
                        elif difficulty == "intermediate":
                            difficulty = "advanced"
                    elif recent_trend < -5:  # Ухудшается
                        if difficulty == "advanced":
                            difficulty = "intermediate"
                        elif difficulty == "intermediate":
                            difficulty = "beginner"
                
                return {
                    "difficulty": difficulty,
                    "confidence": confidence,
                    "avg_score": avg_score,
                    "completion_rate": completion_rate,
                    "trend": recent_trend if len(scores) >= 3 else 0,
                    "session_count": len(sessions)
                }
                
        except Exception as e:
            logger.error(f"Error calculating adaptive difficulty: {e}")
            return {"difficulty": "beginner", "confidence": 0.5}
    
    async def get_similar_students(
        self,
        student_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Поиск похожих студентов для collaborative filtering"""
        try:
            async with get_db_session() as session:
                # Получаем профиль текущего студента
                current_profile = await self._build_student_profile(session, student_id)
                
                # Получаем профили других студентов
                all_students = await session.execute(
                    select(Student).where(Student.id != student_id)
                )
                students = all_students.scalars().all()
                
                similarities = []
                
                for student in students:
                    other_profile = await self._build_student_profile(session, student.id)
                    similarity = await self._calculate_student_similarity(current_profile, other_profile)
                    
                    if similarity > 0.1:  # Минимальный порог схожести
                        similarities.append({
                            "student_id": student.id,
                            "username": student.telegram_username,
                            "display_name": student.display_name,
                            "similarity": similarity,
                            "common_skills": self._find_common_skills(current_profile, other_profile),
                            "level": student.current_level
                        })
                
                # Сортируем по схожести
                similarities.sort(key=lambda x: x["similarity"], reverse=True)
                return similarities[:limit]
                
        except Exception as e:
            logger.error(f"Error finding similar students: {e}")
            return []
    
    async def predict_lesson_success(
        self,
        student_id: int,
        lesson_id: int
    ) -> Dict[str, Any]:
        """Предсказание успешности прохождения урока"""
        try:
            async with get_db_session() as session:
                # Получаем профиль студента
                student_profile = await self._build_student_profile(session, student_id)
                
                # Получаем информацию об уроке (здесь нужно подключение к Lesson Service)
                # Пока используем заглушку
                lesson_difficulty = "intermediate"  # Получить из Lesson Service
                lesson_skills = ["grammar", "vocabulary"]  # Получить из Lesson Service
                
                # Анализируем готовность студента
                readiness_factors = []
                
                # Фактор 1: Соответствие навыков
                skill_readiness = 0
                for skill in lesson_skills:
                    if skill in student_profile["skills"]:
                        skill_readiness += student_profile["skills"][skill]["level"] / 10
                skill_readiness = skill_readiness / len(lesson_skills) if lesson_skills else 0
                readiness_factors.append(("skills", skill_readiness))
                
                # Фактор 2: Общая производительность
                performance_factor = student_profile["performance"]["avg_score"] / 100
                readiness_factors.append(("performance", performance_factor))
                
                # Фактор 3: Соответствие сложности
                student_level_map = {"beginner": 0.3, "intermediate": 0.6, "advanced": 1.0}
                lesson_level_map = {"beginner": 0.3, "intermediate": 0.6, "advanced": 1.0}
                
                student_level_score = student_level_map.get(student_profile["difficulty"], 0.5)
                lesson_level_score = lesson_level_map.get(lesson_difficulty, 0.5)
                
                difficulty_match = 1 - abs(student_level_score - lesson_level_score)
                readiness_factors.append(("difficulty", difficulty_match))
                
                # Фактор 4: Консистентность обучения
                consistency_factor = min(1.0, student_profile["activity"]["streak"] / 7)
                readiness_factors.append(("consistency", consistency_factor))
                
                # Рассчитываем общую вероятность успеха
                weights = {"skills": 0.4, "performance": 0.3, "difficulty": 0.2, "consistency": 0.1}
                success_probability = sum(
                    weights[factor] * score for factor, score in readiness_factors
                )
                
                # Определяем рекомендации
                recommendations = []
                if skill_readiness < 0.6:
                    recommendations.append("Повторите материалы по соответствующим навыкам")
                if performance_factor < 0.7:
                    recommendations.append("Выполните дополнительные упражнения")
                if difficulty_match < 0.7:
                    recommendations.append("Рассмотрите урок другого уровня сложности")
                if consistency_factor < 0.5:
                    recommendations.append("Улучшите регулярность занятий")
                
                return {
                    "lesson_id": lesson_id,
                    "success_probability": success_probability,
                    "confidence": "high" if success_probability > 0.8 else "medium" if success_probability > 0.5 else "low",
                    "readiness_factors": dict(readiness_factors),
                    "recommendations": recommendations,
                    "estimated_time": self._estimate_completion_time(student_profile, lesson_difficulty),
                    "difficulty_match": difficulty_match
                }
                
        except Exception as e:
            logger.error(f"Error predicting lesson success: {e}")
            return {"success_probability": 0.5, "confidence": "unknown"}
    
    async def _build_student_profile(self, session: AsyncSession, student_id: int) -> Dict[str, Any]:
        """Построение полного профиля студента"""
        # Получаем базовую информацию
        student = await session.get(Student, student_id)
        if not student:
            return {}
        
        # Получаем прогресс
        progress_result = await session.execute(
            select(LearningProgress).where(LearningProgress.student_id == student_id)
        )
        progress = progress_result.scalar_one_or_none()
        
        # Получаем навыки
        skills_result = await session.execute(
            select(SkillProgress).where(SkillProgress.student_id == student_id)
        )
        skills = skills_result.scalars().all()
        
        # Получаем недавние сессии
        sessions_result = await session.execute(
            select(StudySession)
            .where(
                and_(
                    StudySession.student_id == student_id,
                    StudySession.created_at >= datetime.utcnow() - timedelta(days=30)
                )
            )
            .order_by(desc(StudySession.created_at))
        )
        recent_sessions = sessions_result.scalars().all()
        
        # Анализируем предпочтения
        preferences = self._analyze_preferences(recent_sessions)
        
        return {
            "student_id": student_id,
            "level": student.current_level,
            "total_xp": student.total_xp,
            "skills": {
                skill.skill_name: {
                    "level": skill.current_level,
                    "progress": skill.progress_percent,
                    "practice_count": skill.practice_count
                }
                for skill in skills
            },
            "progress": {
                "completion_rate": float(progress.overall_completion) if progress else 0,
                "lessons_completed": progress.lessons_completed if progress else 0,
                "avg_score": float(progress.average_score or 0) if progress else 0
            },
            "activity": {
                "streak": progress.current_streak if progress else 0,
                "last_activity": progress.last_activity if progress else None,
                "session_count": len(recent_sessions)
            },
            "performance": {
                "avg_score": sum(s.score for s in recent_sessions if s.score) / len([s for s in recent_sessions if s.score]) if recent_sessions else 0,
                "completion_rate": len([s for s in recent_sessions if s.completed]) / len(recent_sessions) * 100 if recent_sessions else 0
            },
            "preferences": preferences,
            "difficulty": await self.get_adaptive_difficulty(student_id, None)
        }
    
    def _analyze_preferences(self, sessions: List[StudySession]) -> Dict[str, Any]:
        """Анализ предпочтений студента"""
        if not sessions:
            return {}
        
        # Анализируем время занятий
        hours = [s.created_at.hour for s in sessions]
        preferred_time = max(set(hours), key=hours.count) if hours else 12
        
        # Анализируем продолжительность сессий
        durations = [s.duration for s in sessions if s.duration]
        avg_session_duration = sum(durations) / len(durations) if durations else 30
        
        # Анализируем предпочитаемые навыки
        all_skills = []
        for session in sessions:
            all_skills.extend(session.skills_practiced or [])
        
        skill_preferences = {}
        if all_skills:
            skill_counts = {skill: all_skills.count(skill) for skill in set(all_skills)}
            total_skills = len(all_skills)
            skill_preferences = {
                skill: count / total_skills 
                for skill, count in skill_counts.items()
            }
        
        return {
            "preferred_time": preferred_time,
            "avg_session_duration": avg_session_duration,
            "skill_preferences": skill_preferences,
            "total_sessions": len(sessions)
        }
    
    async def _calculate_student_similarity(
        self, 
        profile1: Dict[str, Any], 
        profile2: Dict[str, Any]
    ) -> float:
        """Вычисление схожести между двумя студентами"""
        try:
            similarity_factors = []
            
            # Схожесть по уровню
            level_diff = abs(profile1.get("level", 1) - profile2.get("level", 1))
            level_similarity = max(0, 1 - level_diff / 10)  # Нормализация на 10 уровней
            similarity_factors.append(("level", level_similarity, 0.2))
            
            # Схожесть по навыкам
            skills1 = profile1.get("skills", {})
            skills2 = profile2.get("skills", {})
            common_skills = set(skills1.keys()) & set(skills2.keys())
            
            if common_skills:
                skill_similarities = []
                for skill in common_skills:
                    skill_diff = abs(skills1[skill]["level"] - skills2[skill]["level"])
                    skill_similarity = max(0, 1 - skill_diff / 10)
                    skill_similarities.append(skill_similarity)
                
                avg_skill_similarity = sum(skill_similarities) / len(skill_similarities)
                similarity_factors.append(("skills", avg_skill_similarity, 0.3))
            
            # Схожесть по производительности
            perf1 = profile1.get("performance", {}).get("avg_score", 0)
            perf2 = profile2.get("performance", {}).get("avg_score", 0)
            perf_diff = abs(perf1 - perf2)
            perf_similarity = max(0, 1 - perf_diff / 100)
            similarity_factors.append(("performance", perf_similarity, 0.25))
            
            # Схожесть по предпочтениям времени
            pref1 = profile1.get("preferences", {}).get("preferred_time", 12)
            pref2 = profile2.get("preferences", {}).get("preferred_time", 12)
            time_diff = min(abs(pref1 - pref2), 24 - abs(pref1 - pref2))  # Учитываем цикличность
            time_similarity = max(0, 1 - time_diff / 12)
            similarity_factors.append(("time_preference", time_similarity, 0.1))
            
            # Схожесть по активности
            activity1 = profile1.get("activity", {}).get("session_count", 0)
            activity2 = profile2.get("activity", {}).get("session_count", 0)
            max_activity = max(activity1, activity2, 1)
            activity_similarity = min(activity1, activity2) / max_activity
            similarity_factors.append(("activity", activity_similarity, 0.15))
            
            # Вычисляем взвешенную сумму
            total_similarity = sum(
                score * weight for _, score, weight in similarity_factors
            )
            
            return total_similarity
            
        except Exception as e:
            logger.error(f"Error calculating student similarity: {e}")
            return 0.0
    
    def _find_common_skills(self, profile1: Dict[str, Any], profile2: Dict[str, Any]) -> List[str]:
        """Поиск общих навыков между студентами"""
        skills1 = set(profile1.get("skills", {}).keys())
        skills2 = set(profile2.get("skills", {}).keys())
        return list(skills1 & skills2)
    
    async def _recommend_next_lessons(
        self, 
        session: AsyncSession, 
        student_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Рекомендации следующих уроков"""
        recommendations = []
        
        # Здесь нужно интеграция с Lesson Service для получения доступных уроков
        # Пока возвращаем заглушки
        
        sample_lessons = [
            {"id": 101, "title": "Present Simple Tense", "difficulty": "beginner", "skills": ["grammar"]},
            {"id": 102, "title": "Common Vocabulary", "difficulty": "beginner", "skills": ["vocabulary"]},
            {"id": 201, "title": "Past Tense Forms", "difficulty": "intermediate", "skills": ["grammar"]},
        ]
        
        student_difficulty = student_profile.get("difficulty", {}).get("difficulty", "beginner")
        
        for lesson in sample_lessons:
            if lesson["difficulty"] == student_difficulty:
                success_prediction = await self.predict_lesson_success(
                    student_profile["student_id"], 
                    lesson["id"]
                )
                
                recommendations.append({
                    "type": "next_lesson",
                    "title": f"Изучить урок: {lesson['title']}",
                    "description": f"Рекомендуемый урок уровня {lesson['difficulty']}",
                    "lesson_id": lesson["id"],
                    "relevance_score": success_prediction["success_probability"] * 100,
                    "success_probability": success_prediction["success_probability"],
                    "metadata": {
                        "difficulty": lesson["difficulty"],
                        "skills": lesson["skills"],
                        "estimated_time": success_prediction.get("estimated_time", 30)
                    }
                })
        
        return recommendations
    
    async def _recommend_review_materials(
        self,
        session: AsyncSession,
        student_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Рекомендации материалов для повторения"""
        recommendations = []
        
        # Находим навыки требующие внимания
        skills = student_profile.get("skills", {})
        weak_skills = [
            skill for skill, data in skills.items()
            if data["level"] < 5 or data["progress"] < 70
        ]
        
        for skill in weak_skills[:3]:  # Топ-3 навыка для улучшения
            recommendations.append({
                "type": "review_material",
                "title": f"Повторить материалы по {skill}",
                "description": f"Улучшить навык {skill} с {skills[skill]['level']} уровня",
                "relevance_score": (10 - skills[skill]["level"]) * 10,
                "metadata": {
                    "skill": skill,
                    "current_level": skills[skill]["level"],
                    "target_improvement": 2
                }
            })
        
        return recommendations
    
    async def _recommend_skill_improvements(
        self,
        session: AsyncSession,
        student_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Рекомендации по улучшению навыков"""
        recommendations = []
        
        skills = student_profile.get("skills", {})
        
        # Находим навыки с потенциалом роста
        for skill, data in skills.items():
            if data["level"] < 8 and data["practice_count"] > 5:
                growth_potential = (10 - data["level"]) * (data["practice_count"] / 10)
                
                recommendations.append({
                    "type": "skill_improvement",
                    "title": f"Развить навык {skill}",
                    "description": f"Поднять уровень {skill} с {data['level']} до {data['level'] + 1}",
                    "relevance_score": growth_potential * 10,
                    "metadata": {
                        "skill": skill,
                        "current_level": data["level"],
                        "practice_count": data["practice_count"],
                        "target_level": data["level"] + 1
                    }
                })
        
        return recommendations
    
    async def _recommend_study_schedule(
        self,
        session: AsyncSession,
        student_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Рекомендации по расписанию занятий"""
        recommendations = []
        
        activity = student_profile.get("activity", {})
        preferences = student_profile.get("preferences", {})
        
        # Анализируем текущую активность
        current_streak = activity.get("streak", 0)
        session_count = activity.get("session_count", 0)
        
        if current_streak < 3:
            recommendations.append({
                "type": "study_schedule",
                "title": "Улучшить регулярность занятий",
                "description": "Занимайтесь каждый день в одно и то же время",
                "relevance_score": (7 - current_streak) * 15,
                "metadata": {
                    "current_streak": current_streak,
                    "target_streak": 7,
                    "recommended_time": preferences.get("preferred_time", 19)
                }
            })
        
        if session_count < 10:  # Мало занятий в месяц
            recommendations.append({
                "type": "study_schedule", 
                "title": "Увеличить частоту занятий",
                "description": "Стремитесь к 3-4 занятиям в неделю",
                "relevance_score": (15 - session_count) * 5,
                "metadata": {
                    "current_frequency": session_count / 4,  # в неделю
                    "target_frequency": 4,
                    "duration": preferences.get("avg_session_duration", 30)
                }
            })
        
        return recommendations
    
    async def _recommend_material_types(
        self,
        session: AsyncSession,
        student_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Рекомендации типов материалов"""
        recommendations = []
        
        preferences = student_profile.get("preferences", {})
        skill_preferences = preferences.get("skill_preferences", {})
        
        # Рекомендуем материалы на основе предпочтений навыков
        for skill, preference_score in skill_preferences.items():
            if preference_score > 0.3:  # Высокое предпочтение
                material_types = {
                    "grammar": "интерактивные упражнения по грамматике",
                    "vocabulary": "карточки со словами",
                    "speaking": "аудио-диалоги", 
                    "listening": "подкасты и аудиоматериалы",
                    "reading": "тексты для чтения",
                    "writing": "письменные задания"
                }
                
                if skill in material_types:
                    recommendations.append({
                        "type": "material_type",
                        "title": f"Изучайте {material_types[skill]}",
                        "description": f"Материалы по {skill} показывают хорошие результаты",
                        "relevance_score": preference_score * 100,
                        "metadata": {
                            "skill": skill,
                            "material_type": material_types[skill],
                            "preference_score": preference_score
                        }
                    })
        
        return recommendations
    
    def _estimate_completion_time(self, student_profile: Dict[str, Any], lesson_difficulty: str) -> int:
        """Оценка времени завершения урока"""
        base_times = {
            "beginner": 20,
            "intermediate": 30, 
            "advanced": 45
        }
        
        base_time = base_times.get(lesson_difficulty, 30)
        
        # Корректируем на основе производительности студента
        performance = student_profile.get("performance", {}).get("avg_score", 70)
        if performance < 50:
            modifier = 1.5  # Медленнее
        elif performance > 85:
            modifier = 0.8  # Быстрее
        else:
            modifier = 1.0
        
        return int(base_time * modifier)