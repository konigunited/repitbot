# -*- coding: utf-8 -*-
"""
Recommendations API Router
API для персонализированных рекомендаций
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging

from ...services.recommendation_service import RecommendationService
from ...schemas.student import RecommendationResponse, DifficultyPrediction, SimilarStudentsResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"]
)

recommendation_service = RecommendationService()

@router.get("/{student_id}", response_model=List[RecommendationResponse])
async def get_student_recommendations(
    student_id: int,
    recommendation_type: Optional[str] = Query("all", regex="^(all|next_lesson|review_material|skill_improvement|study_schedule|material_type)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Получение персонализированных рекомендаций для студента
    
    Args:
        student_id: ID студента
        recommendation_type: Тип рекомендаций (all, next_lesson, review_material, skill_improvement, study_schedule, material_type)
        limit: Количество рекомендаций (1-50)
    
    Returns:
        Список персонализированных рекомендаций
    """
    try:
        recommendations = await recommendation_service.get_personalized_recommendations(
            student_id=student_id,
            recommendation_type=recommendation_type,
            limit=limit
        )
        
        return [
            RecommendationResponse(
                type=rec["type"],
                title=rec["title"],
                description=rec["description"],
                relevance_score=rec.get("relevance_score", 0),
                metadata=rec.get("metadata", {})
            )
            for rec in recommendations
        ]
        
    except Exception as e:
        logger.error(f"Error getting recommendations for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения рекомендаций")

@router.get("/{student_id}/adaptive-difficulty")
async def get_adaptive_difficulty(
    student_id: int,
    subject_id: Optional[int] = Query(None, description="ID предмета для специфических рекомендаций")
):
    """
    Получение адаптивного уровня сложности для студента
    
    Args:
        student_id: ID студента
        subject_id: ID предмета (опционально)
    
    Returns:
        Рекомендуемый уровень сложности
    """
    try:
        difficulty_info = await recommendation_service.get_adaptive_difficulty(
            student_id=student_id,
            subject_id=subject_id
        )
        
        return DifficultyPrediction(**difficulty_info)
        
    except Exception as e:
        logger.error(f"Error getting adaptive difficulty for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка определения уровня сложности")

@router.get("/{student_id}/similar-students", response_model=SimilarStudentsResponse)
async def get_similar_students(
    student_id: int,
    limit: int = Query(5, ge=1, le=20)
):
    """
    Поиск похожих студентов для collaborative filtering
    
    Args:
        student_id: ID студента
        limit: Количество похожих студентов (1-20)
    
    Returns:
        Список похожих студентов с коэффициентом схожести
    """
    try:
        similar_students = await recommendation_service.get_similar_students(
            student_id=student_id,
            limit=limit
        )
        
        return SimilarStudentsResponse(
            student_id=student_id,
            similar_students=similar_students,
            total_found=len(similar_students)
        )
        
    except Exception as e:
        logger.error(f"Error finding similar students for {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска похожих студентов")

@router.post("/{student_id}/predict-lesson-success/{lesson_id}")
async def predict_lesson_success(
    student_id: int,
    lesson_id: int
):
    """
    Предсказание успешности прохождения урока студентом
    
    Args:
        student_id: ID студента
        lesson_id: ID урока
    
    Returns:
        Предсказание успешности с рекомендациями
    """
    try:
        prediction = await recommendation_service.predict_lesson_success(
            student_id=student_id,
            lesson_id=lesson_id
        )
        
        return prediction
        
    except Exception as e:
        logger.error(f"Error predicting lesson success for student {student_id}, lesson {lesson_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка предсказания успешности урока")

@router.get("/{student_id}/learning-path")
async def get_personalized_learning_path(
    student_id: int,
    weeks: int = Query(4, ge=1, le=12, description="Количество недель для планирования"),
    hours_per_week: int = Query(5, ge=1, le=20, description="Часов в неделю на обучение")
):
    """
    Получение персонализированного плана обучения
    
    Args:
        student_id: ID студента
        weeks: Количество недель для планирования (1-12)
        hours_per_week: Часов в неделю (1-20)
    
    Returns:
        Персонализированный план обучения
    """
    try:
        # Получаем рекомендации разных типов
        lesson_recommendations = await recommendation_service.get_personalized_recommendations(
            student_id=student_id,
            recommendation_type="next_lesson",
            limit=weeks * 3  # ~3 урока в неделю
        )
        
        skill_recommendations = await recommendation_service.get_personalized_recommendations(
            student_id=student_id,
            recommendation_type="skill_improvement",
            limit=5
        )
        
        schedule_recommendations = await recommendation_service.get_personalized_recommendations(
            student_id=student_id,
            recommendation_type="study_schedule",
            limit=3
        )
        
        # Формируем план обучения
        learning_path = {
            "student_id": student_id,
            "duration_weeks": weeks,
            "hours_per_week": hours_per_week,
            "total_hours": weeks * hours_per_week,
            "recommended_lessons": lesson_recommendations,
            "skill_focus_areas": skill_recommendations,
            "schedule_recommendations": schedule_recommendations,
            "weekly_breakdown": []
        }
        
        # Распределяем уроки по неделям
        lessons_per_week = len(lesson_recommendations) // weeks if weeks > 0 else 0
        for week in range(1, weeks + 1):
            start_idx = (week - 1) * lessons_per_week
            end_idx = week * lessons_per_week
            week_lessons = lesson_recommendations[start_idx:end_idx]
            
            learning_path["weekly_breakdown"].append({
                "week": week,
                "recommended_lessons": week_lessons,
                "estimated_hours": hours_per_week,
                "focus_skills": [rec["metadata"]["skill"] for rec in skill_recommendations[:2]] if skill_recommendations else []
            })
        
        return learning_path
        
    except Exception as e:
        logger.error(f"Error creating learning path for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания плана обучения")

@router.post("/{student_id}/feedback")
async def submit_recommendation_feedback(
    student_id: int,
    recommendation_id: str,
    feedback_type: str = Query(..., regex="^(helpful|not_helpful|completed|ignored)$"),
    feedback_score: Optional[int] = Query(None, ge=1, le=5),
    comments: Optional[str] = None
):
    """
    Отправка отзыва о рекомендации для улучшения алгоритма
    
    Args:
        student_id: ID студента
        recommendation_id: ID рекомендации
        feedback_type: Тип отзыва (helpful, not_helpful, completed, ignored)
        feedback_score: Оценка от 1 до 5
        comments: Дополнительные комментарии
    
    Returns:
        Подтверждение получения отзыва
    """
    try:
        # Здесь можно реализовать сохранение отзывов в базу данных
        # для дальнейшего обучения рекомендательной системы
        
        feedback_data = {
            "student_id": student_id,
            "recommendation_id": recommendation_id,
            "feedback_type": feedback_type,
            "feedback_score": feedback_score,
            "comments": comments,
            "timestamp": "now"  # В реальной реализации - datetime.utcnow()
        }
        
        logger.info(f"Received recommendation feedback: {feedback_data}")
        
        return {
            "message": "Отзыв получен и учтен для улучшения рекомендаций",
            "feedback_id": f"fb_{student_id}_{recommendation_id}",
            "status": "received"
        }
        
    except Exception as e:
        logger.error(f"Error processing recommendation feedback: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обработки отзыва")

@router.get("/{student_id}/recommendation-stats")
async def get_recommendation_statistics(
    student_id: int,
    period_days: int = Query(30, ge=1, le=365)
):
    """
    Получение статистики по рекомендациям студента
    
    Args:
        student_id: ID студента
        period_days: Период в днях для анализа (1-365)
    
    Returns:
        Статистика эффективности рекомендаций
    """
    try:
        # В реальной реализации здесь будет анализ из базы данных
        stats = {
            "student_id": student_id,
            "period_days": period_days,
            "recommendations_given": 45,  # Заглушка
            "recommendations_completed": 32,
            "completion_rate": 71.1,
            "average_rating": 4.2,
            "most_helpful_type": "next_lesson",
            "least_helpful_type": "material_type",
            "improvement_in_performance": 12.5,
            "recommendation_accuracy": 78.3
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting recommendation statistics for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики рекомендаций")