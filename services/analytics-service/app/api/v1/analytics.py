"""
Analytics API endpoints
Provides analytics data and dashboard endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from ...services.lesson_analytics import LessonAnalyticsService
from ...services.payment_analytics import PaymentAnalyticsService
from ...services.user_analytics import UserAnalyticsService
from ...services.material_analytics import MaterialAnalyticsService
from ...auth.jwt_auth import get_current_user
from ...models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Dependency injection for services
def get_lesson_service() -> LessonAnalyticsService:
    return LessonAnalyticsService()

def get_payment_service() -> PaymentAnalyticsService:
    return PaymentAnalyticsService()

def get_user_service() -> UserAnalyticsService:
    return UserAnalyticsService()

def get_material_service() -> MaterialAnalyticsService:
    return MaterialAnalyticsService()

@router.get("/dashboard/{role}")
async def get_dashboard_by_role(
    role: str,
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    tutor_id: Optional[int] = Query(None, description="Filter by tutor ID"),
    current_user: User = Depends(get_current_user),
    lesson_service: LessonAnalyticsService = Depends(get_lesson_service),
    payment_service: PaymentAnalyticsService = Depends(get_payment_service),
    user_service: UserAnalyticsService = Depends(get_user_service),
    material_service: MaterialAnalyticsService = Depends(get_material_service)
) -> Dict[str, Any]:
    """Get dashboard data based on user role"""
    try:
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Validate role
        valid_roles = ["admin", "tutor", "parent", "student"]
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
        
        # Role-based access control
        if role == "tutor" and current_user.role != "admin":
            # Tutors can only see their own data
            if tutor_id and tutor_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied: Can only view own data")
            tutor_id = current_user.id
        elif role in ["parent", "student"] and current_user.role not in ["admin", "tutor"]:
            # Parents/students have limited access
            pass
        elif role == "admin" and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied: Admin role required")
        
        dashboard_data = {}
        
        if role == "admin":
            # Full analytics for admin
            dashboard_data = {
                "lessons": await lesson_service.get_lesson_statistics(start_date, end_date, tutor_id),
                "payments": await payment_service.get_payment_summary(start_date, end_date, tutor_id),
                "users": await user_service.get_activity_summary(start_date, end_date),
                "materials": await material_service.get_usage_summary(start_date, end_date),
                "completion_trends": await lesson_service.get_completion_trends(start_date, end_date, tutor_id),
                "revenue_trends": await payment_service.get_revenue_trends(start_date, end_date, tutor_id),
                "subject_performance": await lesson_service.get_subject_performance(start_date, end_date, tutor_id),
                "tutor_earnings": await payment_service.get_tutor_earnings(start_date, end_date)
            }
        
        elif role == "tutor":
            # Tutor-specific analytics
            dashboard_data = {
                "lessons": await lesson_service.get_lesson_statistics(start_date, end_date, tutor_id),
                "earnings": await payment_service.get_tutor_earnings(start_date, end_date, tutor_id),
                "completion_trends": await lesson_service.get_completion_trends(start_date, end_date, tutor_id),
                "subject_performance": await lesson_service.get_subject_performance(start_date, end_date, tutor_id),
                "homework_analytics": await lesson_service.get_homework_analytics(start_date, end_date, tutor_id),
                "student_progress": await lesson_service.get_student_progress(start_date, end_date, tutor_id)
            }
        
        elif role == "parent":
            # Parent view focused on their children
            student_ids = await user_service.get_children_ids(current_user.id)
            dashboard_data = {
                "children_progress": [],
                "lesson_summary": await lesson_service.get_lesson_statistics(start_date, end_date, student_id=student_ids),
                "homework_completion": await lesson_service.get_homework_analytics(start_date, end_date, student_id=student_ids),
                "payment_history": await payment_service.get_payment_summary(start_date, end_date, parent_id=current_user.id)
            }
            
            # Get progress for each child
            for student_id in student_ids:
                child_progress = await lesson_service.get_student_progress(start_date, end_date, student_id=student_id)
                dashboard_data["children_progress"].append(child_progress)
        
        elif role == "student":
            # Student view of their own progress
            dashboard_data = {
                "lesson_progress": await lesson_service.get_student_progress(start_date, end_date, student_id=current_user.id),
                "homework_stats": await lesson_service.get_homework_analytics(start_date, end_date, student_id=current_user.id),
                "subject_performance": await lesson_service.get_subject_performance(start_date, end_date, student_id=current_user.id),
                "material_usage": await material_service.get_student_material_usage(current_user.id, start_date, end_date)
            }
        
        return {
            "role": role,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "data": dashboard_data,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard for role {role}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")

@router.get("/lessons/stats")
async def get_lesson_statistics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    lesson_service: LessonAnalyticsService = Depends(get_lesson_service)
) -> Dict[str, Any]:
    """Get detailed lesson statistics"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Access control
        if tutor_id and current_user.role not in ["admin"] and current_user.id != tutor_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        stats = await lesson_service.get_lesson_statistics(start_date, end_date, tutor_id, student_id)
        trends = await lesson_service.get_completion_trends(start_date, end_date, tutor_id, student_id)
        performance = await lesson_service.get_subject_performance(start_date, end_date, tutor_id, student_id)
        homework = await lesson_service.get_homework_analytics(start_date, end_date, tutor_id, student_id)
        
        return {
            "statistics": stats,
            "completion_trends": trends,
            "subject_performance": performance,
            "homework_analytics": homework,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting lesson statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get lesson statistics: {str(e)}")

@router.get("/payments/summary")
async def get_payment_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    payment_service: PaymentAnalyticsService = Depends(get_payment_service)
) -> Dict[str, Any]:
    """Get payment analytics summary"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Access control
        if tutor_id and current_user.role not in ["admin"] and current_user.id != tutor_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        summary = await payment_service.get_payment_summary(start_date, end_date, tutor_id)
        trends = await payment_service.get_revenue_trends(start_date, end_date, tutor_id)
        methods = await payment_service.get_payment_method_distribution(start_date, end_date, tutor_id)
        
        return {
            "summary": summary,
            "revenue_trends": trends,
            "payment_methods": methods,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting payment summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get payment summary: {str(e)}")

@router.get("/users/activity")
async def get_user_activity(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    user_service: UserAnalyticsService = Depends(get_user_service)
) -> Dict[str, Any]:
    """Get user activity analytics"""
    try:
        # Admin only endpoint
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        summary = await user_service.get_activity_summary(start_date, end_date)
        patterns = await user_service.get_login_patterns(start_date, end_date)
        engagement = await user_service.get_engagement_metrics(start_date, end_date)
        distribution = await user_service.get_role_distribution()
        
        return {
            "activity_summary": summary,
            "login_patterns": patterns,
            "engagement_metrics": engagement,
            "role_distribution": distribution,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user activity: {str(e)}")

@router.get("/materials/usage")
async def get_material_usage(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    subject_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    material_service: MaterialAnalyticsService = Depends(get_material_service)
) -> Dict[str, Any]:
    """Get material usage analytics"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        summary = await material_service.get_usage_summary(start_date, end_date)
        popular = await material_service.get_popular_materials(start_date, end_date)
        distribution = await material_service.get_material_distribution_by_subject()
        trends = await material_service.get_upload_trends(start_date, end_date)
        
        return {
            "usage_summary": summary,
            "popular_materials": popular,
            "subject_distribution": distribution,
            "upload_trends": trends,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting material usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get material usage: {str(e)}")

@router.get("/tutors/earnings")
async def get_tutor_earnings(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    payment_service: PaymentAnalyticsService = Depends(get_payment_service)
) -> Dict[str, Any]:
    """Get tutor earnings analytics"""
    try:
        # Access control: admins see all, tutors see only their own
        if current_user.role == "tutor":
            tutor_id = current_user.id
        elif current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        earnings = await payment_service.get_tutor_earnings(start_date, end_date, tutor_id)
        detailed_breakdown = await payment_service.get_tutor_earnings_breakdown(start_date, end_date, tutor_id)
        
        return {
            "earnings": earnings,
            "breakdown": detailed_breakdown,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting tutor earnings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get tutor earnings: {str(e)}")

@router.get("/performance/subjects")
async def get_subject_performance(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    lesson_service: LessonAnalyticsService = Depends(get_lesson_service)
) -> Dict[str, Any]:
    """Get subject performance analytics"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Access control
        if tutor_id and current_user.role not in ["admin"] and current_user.id != tutor_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        performance = await lesson_service.get_subject_performance(start_date, end_date, tutor_id, student_id)
        comparison = await lesson_service.get_subject_comparison(start_date, end_date, tutor_id)
        trends = await lesson_service.get_subject_trends(start_date, end_date, tutor_id, student_id)
        
        return {
            "performance": performance,
            "comparison": comparison,
            "trends": trends,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting subject performance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get subject performance: {str(e)}")

@router.get("/engagement/metrics")
async def get_engagement_metrics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    user_service: UserAnalyticsService = Depends(get_user_service)
) -> Dict[str, Any]:
    """Get user engagement metrics"""
    try:
        # Admin only endpoint
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        metrics = await user_service.get_engagement_metrics(start_date, end_date)
        retention = await user_service.get_retention_metrics(start_date, end_date)
        activity_patterns = await user_service.get_activity_patterns(start_date, end_date)
        
        return {
            "engagement_metrics": metrics,
            "retention_metrics": retention,
            "activity_patterns": activity_patterns,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting engagement metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get engagement metrics: {str(e)}")

@router.get("/homework/analytics")
async def get_homework_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    lesson_service: LessonAnalyticsService = Depends(get_lesson_service)
) -> Dict[str, Any]:
    """Get homework completion and performance analytics"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Access control
        if tutor_id and current_user.role not in ["admin"] and current_user.id != tutor_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        analytics = await lesson_service.get_homework_analytics(start_date, end_date, tutor_id, student_id)
        completion_trends = await lesson_service.get_homework_completion_trends(start_date, end_date, tutor_id, student_id)
        performance = await lesson_service.get_homework_performance(start_date, end_date, tutor_id, student_id)
        
        return {
            "analytics": analytics,
            "completion_trends": completion_trends,
            "performance": performance,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting homework analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get homework analytics: {str(e)}")

@router.get("/overview")
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    lesson_service: LessonAnalyticsService = Depends(get_lesson_service),
    payment_service: PaymentAnalyticsService = Depends(get_payment_service),
    user_service: UserAnalyticsService = Depends(get_user_service),
    material_service: MaterialAnalyticsService = Depends(get_material_service)
) -> Dict[str, Any]:
    """Get high-level analytics overview"""
    try:
        # Get current date range (last 7 days for overview)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Get overview data based on user role
        overview = {}
        
        if current_user.role == "admin":
            overview = {
                "total_lessons": await lesson_service.get_total_lessons_count(),
                "total_revenue": await payment_service.get_total_revenue(),
                "active_users": await user_service.get_active_users_count(start_date, end_date),
                "total_materials": await material_service.get_total_materials_count(),
                "recent_activity": {
                    "lessons_this_week": await lesson_service.get_lessons_count(start_date, end_date),
                    "revenue_this_week": await payment_service.get_revenue_total(start_date, end_date),
                    "new_users_this_week": await user_service.get_new_users_count(start_date, end_date),
                    "materials_uploaded_this_week": await material_service.get_uploads_count(start_date, end_date)
                }
            }
        elif current_user.role == "tutor":
            overview = {
                "my_lessons": await lesson_service.get_tutor_lessons_count(current_user.id),
                "my_earnings": await payment_service.get_tutor_total_earnings(current_user.id),
                "my_students": await lesson_service.get_tutor_students_count(current_user.id),
                "recent_activity": {
                    "lessons_this_week": await lesson_service.get_lessons_count(start_date, end_date, current_user.id),
                    "earnings_this_week": await payment_service.get_revenue_total(start_date, end_date, current_user.id)
                }
            }
        else:
            # Limited overview for parents/students
            overview = {
                "my_lessons": await lesson_service.get_user_lessons_count(current_user.id),
                "completed_lessons": await lesson_service.get_completed_lessons_count(current_user.id),
                "recent_activity": {
                    "lessons_this_week": await lesson_service.get_lessons_count(start_date, end_date, student_id=current_user.id)
                }
            }
        
        return {
            "overview": overview,
            "user_role": current_user.role,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics overview: {str(e)}")