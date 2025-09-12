"""
Analytics Service Client for Telegram Bot
HTTP client for communicating with Analytics Service
"""

import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os
import io
import base64

logger = logging.getLogger(__name__)

class AnalyticsServiceClient:
    """Client for Analytics Service"""
    
    def __init__(self):
        self.base_url = os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:8007")
        self.timeout = 60.0  # Longer timeout for analytics operations
        self.retries = 3
        self.retry_delay = 2.0

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, params=params, headers=headers)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=data, headers=headers)
                    elif method.upper() == "PUT":
                        response = await client.put(url, json=data, headers=headers)
                    elif method.upper() == "DELETE":
                        response = await client.delete(url, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.RequestError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.retries}): {str(e)}")
                if attempt < self.retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All retry attempts failed for {url}")
                    return None
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {str(e)}")
                return None
        
        return None

    async def get_user_dashboard(
        self,
        user_role: str,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Optional[Dict]:
        """Get dashboard data for user role"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            
            if user_role == "tutor" and user_id:
                params["tutor_id"] = user_id
            
            result = await self._make_request(
                "GET", 
                f"/api/v1/analytics/dashboard/{user_role}",
                params=params
            )
            return result
            
        except Exception as e:
            logger.error(f"Error getting user dashboard: {str(e)}")
            return None

    async def get_lesson_statistics(
        self,
        tutor_id: Optional[int] = None,
        student_id: Optional[int] = None,
        days: int = 30
    ) -> Optional[Dict]:
        """Get lesson statistics"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            
            if tutor_id:
                params["tutor_id"] = tutor_id
            if student_id:
                params["student_id"] = student_id
            
            result = await self._make_request(
                "GET", 
                "/api/v1/analytics/lessons/stats",
                params=params
            )
            return result
            
        except Exception as e:
            logger.error(f"Error getting lesson statistics: {str(e)}")
            return None

    async def get_payment_summary(
        self,
        tutor_id: Optional[int] = None,
        days: int = 30
    ) -> Optional[Dict]:
        """Get payment summary"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            
            if tutor_id:
                params["tutor_id"] = tutor_id
            
            result = await self._make_request(
                "GET", 
                "/api/v1/analytics/payments/summary",
                params=params
            )
            return result
            
        except Exception as e:
            logger.error(f"Error getting payment summary: {str(e)}")
            return None

    async def get_tutor_earnings(
        self,
        tutor_id: Optional[int] = None,
        days: int = 30
    ) -> Optional[Dict]:
        """Get tutor earnings"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            
            if tutor_id:
                params["tutor_id"] = tutor_id
            
            result = await self._make_request(
                "GET", 
                "/api/v1/analytics/tutors/earnings",
                params=params
            )
            return result
            
        except Exception as e:
            logger.error(f"Error getting tutor earnings: {str(e)}")
            return None

    async def get_subject_performance(
        self,
        tutor_id: Optional[int] = None,
        student_id: Optional[int] = None,
        days: int = 30
    ) -> Optional[Dict]:
        """Get subject performance analytics"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            
            if tutor_id:
                params["tutor_id"] = tutor_id
            if student_id:
                params["student_id"] = student_id
            
            result = await self._make_request(
                "GET", 
                "/api/v1/analytics/performance/subjects",
                params=params
            )
            return result
            
        except Exception as e:
            logger.error(f"Error getting subject performance: {str(e)}")
            return None

    async def get_homework_analytics(
        self,
        tutor_id: Optional[int] = None,
        student_id: Optional[int] = None,
        days: int = 30
    ) -> Optional[Dict]:
        """Get homework analytics"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            
            if tutor_id:
                params["tutor_id"] = tutor_id
            if student_id:
                params["student_id"] = student_id
            
            result = await self._make_request(
                "GET", 
                "/api/v1/analytics/homework/analytics",
                params=params
            )
            return result
            
        except Exception as e:
            logger.error(f"Error getting homework analytics: {str(e)}")
            return None

    async def generate_chart(
        self,
        chart_type: str,
        parameters: Dict[str, Any]
    ) -> Optional[Dict]:
        """Generate analytics chart"""
        try:
            endpoint_map = {
                "lesson_completion": "/api/v1/charts/lessons/completion",
                "subject_performance": "/api/v1/charts/subjects/performance",
                "revenue_trends": "/api/v1/charts/revenue/trends",
                "tutor_earnings": "/api/v1/charts/tutors/earnings",
                "user_activity": "/api/v1/charts/users/activity",
                "material_usage": "/api/v1/charts/materials/usage"
            }
            
            endpoint = endpoint_map.get(chart_type)
            if not endpoint:
                logger.error(f"Unknown chart type: {chart_type}")
                return None
            
            result = await self._make_request("GET", endpoint, params=parameters)
            return result
            
        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return None

    async def generate_quick_report(
        self,
        report_type: str,
        days: int = 7,
        format: str = "pdf"
    ) -> Optional[bytes]:
        """Generate quick report and return file data"""
        try:
            params = {
                "days": days,
                "format": format
            }
            
            url = f"{self.base_url}/api/v1/reports/quick/{report_type}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.content
                
        except Exception as e:
            logger.error(f"Error generating quick report: {str(e)}")
            return None

    async def start_report_generation(
        self,
        report_type: str,
        parameters: Dict[str, Any]
    ) -> Optional[str]:
        """Start report generation and return task ID"""
        try:
            data = {
                "report_type": report_type,
                **parameters
            }
            
            result = await self._make_request(
                "POST", 
                "/api/v1/reports/generate",
                params=data
            )
            return result.get("task_id") if result else None
            
        except Exception as e:
            logger.error(f"Error starting report generation: {str(e)}")
            return None

    async def get_report_status(self, task_id: str) -> Optional[Dict]:
        """Get report generation status"""
        try:
            result = await self._make_request(
                "GET", 
                f"/api/v1/reports/status/{task_id}"
            )
            return result
            
        except Exception as e:
            logger.error(f"Error getting report status: {str(e)}")
            return None

    async def get_analytics_overview(self) -> Optional[Dict]:
        """Get high-level analytics overview"""
        try:
            result = await self._make_request("GET", "/api/v1/analytics/overview")
            return result
            
        except Exception as e:
            logger.error(f"Error getting analytics overview: {str(e)}")
            return None

    async def get_available_chart_types(self) -> Optional[Dict]:
        """Get available chart types and configurations"""
        try:
            result = await self._make_request("GET", "/api/v1/charts/types")
            return result
            
        except Exception as e:
            logger.error(f"Error getting chart types: {str(e)}")
            return None

    async def get_report_templates(self) -> Optional[Dict]:
        """Get available report templates"""
        try:
            result = await self._make_request("GET", "/api/v1/reports/templates")
            return result
            
        except Exception as e:
            logger.error(f"Error getting report templates: {str(e)}")
            return None

    def format_statistics_message(self, stats: Dict[str, Any]) -> str:
        """Format statistics data into readable Telegram message"""
        try:
            if not stats:
                return "📊 Статистика недоступна"
            
            message = "📊 **Статистика**\n\n"
            
            # Lesson statistics
            if "lesson_stats" in stats or "statistics" in stats:
                lesson_data = stats.get("lesson_stats") or stats.get("statistics", {})
                message += "📚 **Уроки:**\n"
                message += f"• Всего уроков: {lesson_data.get('total_lessons', 0)}\n"
                message += f"• Завершено: {lesson_data.get('completed_lessons', 0)}\n"
                message += f"• Отменено: {lesson_data.get('cancelled_lessons', 0)}\n"
                message += f"• Процент завершения: {lesson_data.get('completion_rate', 0):.1f}%\n\n"
            
            # Payment statistics
            if "payment_summary" in stats or "summary" in stats:
                payment_data = stats.get("payment_summary") or stats.get("summary", {})
                message += "💰 **Платежи:**\n"
                message += f"• Общая сумма: {payment_data.get('total_revenue', 0)} руб.\n"
                message += f"• Количество платежей: {payment_data.get('total_payments', 0)}\n"
                message += f"• Средний чек: {payment_data.get('average_payment', 0)} руб.\n\n"
            
            # Homework statistics
            if "homework_analytics" in stats or "homework_stats" in stats:
                homework_data = stats.get("homework_analytics") or stats.get("homework_stats", {})
                message += "📝 **Домашние задания:**\n"
                message += f"• Выдано заданий: {homework_data.get('total_assignments', 0)}\n"
                message += f"• Выполнено: {homework_data.get('completed_assignments', 0)}\n"
                message += f"• Средняя оценка: {homework_data.get('average_grade', 0):.1f}\n\n"
            
            # Period information
            if "period" in stats:
                period = stats["period"]
                message += f"📅 **Период:** {period.get('start_date', '')} - {period.get('end_date', '')}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting statistics message: {str(e)}")
            return "📊 Ошибка при форматировании статистики"

    def format_earnings_message(self, earnings: Dict[str, Any]) -> str:
        """Format earnings data into readable Telegram message"""
        try:
            if not earnings:
                return "💰 Данные о доходах недоступны"
            
            message = "💰 **Доходы**\n\n"
            
            if "earnings" in earnings:
                earnings_data = earnings["earnings"]
                if isinstance(earnings_data, list) and earnings_data:
                    # Multiple tutors
                    for tutor in earnings_data:
                        message += f"👨‍🏫 {tutor.get('tutor_name', 'Неизвестный')}:\n"
                        message += f"• Доход: {tutor.get('total_earnings', 0)} руб.\n"
                        message += f"• Уроков: {tutor.get('lesson_count', 0)}\n\n"
                elif isinstance(earnings_data, dict):
                    # Single tutor
                    message += f"• Общий доход: {earnings_data.get('total_earnings', 0)} руб.\n"
                    message += f"• Количество уроков: {earnings_data.get('lesson_count', 0)}\n"
                    message += f"• Средний доход за урок: {earnings_data.get('average_per_lesson', 0)} руб.\n\n"
            
            # Period information
            if "period" in earnings:
                period = earnings["period"]
                message += f"📅 **Период:** {period.get('start_date', '')} - {period.get('end_date', '')}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting earnings message: {str(e)}")
            return "💰 Ошибка при форматировании данных о доходах"

    async def health_check(self) -> bool:
        """Check if Analytics Service is healthy"""
        try:
            result = await self._make_request("GET", "/health")
            return result is not None and result.get("status") == "healthy"
            
        except Exception as e:
            logger.error(f"Analytics service health check failed: {str(e)}")
            return False

# Global client instance
analytics_client = AnalyticsServiceClient()