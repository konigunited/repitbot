"""
Reports API endpoints
Provides report generation and download endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import tempfile
import uuid
import asyncio
import logging

from ...services.report_service import ReportService
from ...auth.jwt_auth import get_current_user
from ...models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

# In-memory storage for report generation status
report_tasks = {}

def get_report_service() -> ReportService:
    return ReportService()

@router.post("/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    report_type: str = Query(..., description="Report type: lesson, payment, user_activity, material_usage, comprehensive"),
    format: str = Query("pdf", description="Report format: pdf, excel"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """Generate report and return task ID for tracking"""
    try:
        # Validate report type
        valid_types = ["lesson", "payment", "user_activity", "material_usage", "comprehensive"]
        if report_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid report type. Must be one of: {valid_types}")
        
        # Validate format
        valid_formats = ["pdf", "excel"]
        if format.lower() not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Invalid format. Must be one of: {valid_formats}")
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Access control
        if report_type in ["user_activity"] and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required for this report type")
        
        if tutor_id and current_user.role not in ["admin"] and current_user.id != tutor_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Store task info
        report_tasks[task_id] = {
            "status": "pending",
            "report_type": report_type,
            "format": format,
            "created_at": datetime.now(),
            "user_id": current_user.id,
            "error": None,
            "file_path": None
        }
        
        # Start background task
        background_tasks.add_task(
            generate_report_background,
            task_id,
            report_type,
            format,
            start_date,
            end_date,
            tutor_id,
            student_id,
            report_service
        )
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Report generation started",
            "estimated_time": "30-60 seconds"
        }
        
    except Exception as e:
        logger.error(f"Error starting report generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start report generation: {str(e)}")

async def generate_report_background(
    task_id: str,
    report_type: str,
    format: str,
    start_date: datetime,
    end_date: datetime,
    tutor_id: Optional[int],
    student_id: Optional[int],
    report_service: ReportService
):
    """Background task for report generation"""
    try:
        # Update status
        report_tasks[task_id]["status"] = "processing"
        
        # Generate report based on type
        if report_type == "lesson":
            report_data = await report_service.generate_lesson_report(
                start_date, end_date, tutor_id, student_id, format
            )
        elif report_type == "payment":
            report_data = await report_service.generate_payment_report(
                start_date, end_date, tutor_id, format
            )
        elif report_type == "user_activity":
            report_data = await report_service.generate_user_activity_report(
                start_date, end_date, format
            )
        elif report_type == "material_usage":
            report_data = await report_service.generate_material_usage_report(
                start_date, end_date, format
            )
        elif report_type == "comprehensive":
            report_data = await report_service.generate_comprehensive_report(
                start_date, end_date, tutor_id, format
            )
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        # Save report to temporary file
        file_extension = "pdf" if format == "pdf" else "xlsx"
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{file_extension}",
            prefix=f"{report_type}_report_"
        )
        temp_file.write(report_data)
        temp_file.close()
        
        # Update task status
        report_tasks[task_id].update({
            "status": "completed",
            "file_path": temp_file.name,
            "completed_at": datetime.now()
        })
        
    except Exception as e:
        logger.error(f"Error generating report {task_id}: {str(e)}")
        report_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now()
        })

@router.get("/status/{task_id}")
async def get_report_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get report generation status"""
    try:
        if task_id not in report_tasks:
            raise HTTPException(status_code=404, detail="Report task not found")
        
        task_info = report_tasks[task_id]
        
        # Check if user has access to this task
        if task_info["user_id"] != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        response = {
            "task_id": task_id,
            "status": task_info["status"],
            "report_type": task_info["report_type"],
            "format": task_info["format"],
            "created_at": task_info["created_at"].isoformat()
        }
        
        if task_info["status"] == "completed":
            response["download_url"] = f"/api/v1/reports/download/{task_id}"
            response["completed_at"] = task_info.get("completed_at", datetime.now()).isoformat()
        elif task_info["status"] == "failed":
            response["error"] = task_info.get("error", "Unknown error")
            response["failed_at"] = task_info.get("failed_at", datetime.now()).isoformat()
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting report status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get report status: {str(e)}")

@router.get("/download/{task_id}")
async def download_report(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> FileResponse:
    """Download generated report"""
    try:
        if task_id not in report_tasks:
            raise HTTPException(status_code=404, detail="Report task not found")
        
        task_info = report_tasks[task_id]
        
        # Check if user has access to this task
        if task_info["user_id"] != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        if task_info["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"Report not ready. Status: {task_info['status']}")
        
        file_path = task_info.get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="Report file not found")
        
        # Generate filename
        report_type = task_info["report_type"]
        format_ext = "pdf" if task_info["format"] == "pdf" else "xlsx"
        filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_ext}"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")

@router.get("/templates")
async def get_report_templates(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available report templates and their configurations"""
    try:
        templates = {
            "lesson": {
                "name": "Lesson Analytics Report",
                "description": "Detailed analysis of lesson completion, trends, and performance",
                "parameters": {
                    "start_date": "Start date for analysis (optional, defaults to 30 days ago)",
                    "end_date": "End date for analysis (optional, defaults to today)",
                    "tutor_id": "Filter by specific tutor (optional)",
                    "student_id": "Filter by specific student (optional)"
                },
                "formats": ["pdf", "excel"],
                "estimated_time": "30-45 seconds",
                "access_roles": ["admin", "tutor", "parent", "student"]
            },
            "payment": {
                "name": "Payment Analytics Report",
                "description": "Revenue trends, earnings breakdown, and payment method analysis",
                "parameters": {
                    "start_date": "Start date for analysis (optional)",
                    "end_date": "End date for analysis (optional)",
                    "tutor_id": "Filter by specific tutor (optional)"
                },
                "formats": ["pdf", "excel"],
                "estimated_time": "20-30 seconds",
                "access_roles": ["admin", "tutor"]
            },
            "user_activity": {
                "name": "User Activity Report",
                "description": "User engagement metrics, login patterns, and activity trends",
                "parameters": {
                    "start_date": "Start date for analysis (optional)",
                    "end_date": "End date for analysis (optional)"
                },
                "formats": ["pdf", "excel"],
                "estimated_time": "25-35 seconds",
                "access_roles": ["admin"]
            },
            "material_usage": {
                "name": "Material Usage Report",
                "description": "Material access patterns, popular content, and usage trends",
                "parameters": {
                    "start_date": "Start date for analysis (optional)",
                    "end_date": "End date for analysis (optional)"
                },
                "formats": ["pdf", "excel"],
                "estimated_time": "20-30 seconds",
                "access_roles": ["admin", "tutor", "parent"]
            },
            "comprehensive": {
                "name": "Comprehensive Analytics Report",
                "description": "Complete overview combining all analytics metrics",
                "parameters": {
                    "start_date": "Start date for analysis (optional)",
                    "end_date": "End date for analysis (optional)",
                    "tutor_id": "Filter by specific tutor (optional)"
                },
                "formats": ["pdf", "excel"],
                "estimated_time": "60-90 seconds",
                "access_roles": ["admin", "tutor"]
            }
        }
        
        # Filter templates based on user role
        if current_user.role == "tutor":
            allowed_templates = ["lesson", "payment", "material_usage", "comprehensive"]
            templates = {k: v for k, v in templates.items() if k in allowed_templates}
        elif current_user.role == "parent":
            allowed_templates = ["lesson", "material_usage"]
            templates = {k: v for k, v in templates.items() if k in allowed_templates}
        elif current_user.role == "student":
            allowed_templates = ["lesson"]
            templates = {k: v for k, v in templates.items() if k in allowed_templates}
        
        return {
            "templates": templates,
            "user_role": current_user.role,
            "available_formats": ["pdf", "excel"]
        }
        
    except Exception as e:
        logger.error(f"Error getting report templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get report templates: {str(e)}")

@router.get("/history")
async def get_report_history(
    limit: int = Query(20, description="Maximum number of reports to return"),
    offset: int = Query(0, description="Number of reports to skip"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's report generation history"""
    try:
        # Filter tasks by user (admins can see all)
        user_tasks = []
        for task_id, task_info in report_tasks.items():
            if current_user.role == "admin" or task_info["user_id"] == current_user.id:
                task_data = {
                    "task_id": task_id,
                    "report_type": task_info["report_type"],
                    "format": task_info["format"],
                    "status": task_info["status"],
                    "created_at": task_info["created_at"].isoformat(),
                    "user_id": task_info["user_id"] if current_user.role == "admin" else None
                }
                
                if task_info["status"] == "completed":
                    task_data["completed_at"] = task_info.get("completed_at", datetime.now()).isoformat()
                    task_data["download_available"] = True
                elif task_info["status"] == "failed":
                    task_data["error"] = task_info.get("error", "Unknown error")
                    task_data["failed_at"] = task_info.get("failed_at", datetime.now()).isoformat()
                
                user_tasks.append(task_data)
        
        # Sort by creation date (newest first)
        user_tasks.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        total = len(user_tasks)
        paginated_tasks = user_tasks[offset:offset + limit]
        
        return {
            "reports": paginated_tasks,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
        
    except Exception as e:
        logger.error(f"Error getting report history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get report history: {str(e)}")

@router.delete("/cleanup")
async def cleanup_old_reports(
    days_old: int = Query(7, description="Delete reports older than this many days"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cleanup old report files and tasks (admin only)"""
    try:
        # Admin only endpoint
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned_count = 0
        
        # Find and remove old tasks
        tasks_to_remove = []
        for task_id, task_info in report_tasks.items():
            if task_info["created_at"] < cutoff_date:
                # Remove file if it exists
                if task_info.get("file_path"):
                    try:
                        import os
                        os.unlink(task_info["file_path"])
                    except Exception as e:
                        logger.warning(f"Failed to delete file {task_info['file_path']}: {str(e)}")
                
                tasks_to_remove.append(task_id)
                cleaned_count += 1
        
        # Remove tasks from memory
        for task_id in tasks_to_remove:
            del report_tasks[task_id]
        
        return {
            "cleaned_reports": cleaned_count,
            "cutoff_date": cutoff_date.isoformat(),
            "remaining_reports": len(report_tasks)
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup reports: {str(e)}")

@router.get("/quick/{report_type}")
async def generate_quick_report(
    report_type: str,
    days: int = Query(7, description="Number of days for quick report"),
    format: str = Query("pdf", description="Report format"),
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service)
) -> Response:
    """Generate and immediately return a quick report (for small date ranges)"""
    try:
        # Validate report type
        valid_types = ["lesson", "payment", "material_usage"]
        if report_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid report type for quick generation. Must be one of: {valid_types}")
        
        # Limit days for quick reports
        if days > 30:
            raise HTTPException(status_code=400, detail="Quick reports are limited to 30 days")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Access control
        tutor_id = None
        if current_user.role == "tutor":
            tutor_id = current_user.id
        elif current_user.role not in ["admin", "tutor"] and report_type == "payment":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Generate report
        if report_type == "lesson":
            report_data = await report_service.generate_lesson_report(
                start_date, end_date, tutor_id, None, format
            )
        elif report_type == "payment":
            report_data = await report_service.generate_payment_report(
                start_date, end_date, tutor_id, format
            )
        elif report_type == "material_usage":
            report_data = await report_service.generate_material_usage_report(
                start_date, end_date, format
            )
        
        # Set content type and filename
        content_type = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        file_extension = "pdf" if format == "pdf" else "xlsx"
        filename = f"{report_type}_quick_report_{days}days.{file_extension}"
        
        return Response(
            content=report_data,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error generating quick report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate quick report: {str(e)}")