"""
Charts API endpoints
Provides chart generation and visualization endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import tempfile
import logging

from ...services.chart_service import ChartService
from ...auth.jwt_auth import get_current_user
from ...models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/charts", tags=["charts"])

def get_chart_service() -> ChartService:
    return ChartService()

@router.get("/lessons/completion")
async def get_lesson_completion_chart(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    chart_type: str = Query("line", description="Chart type: line, bar"),
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Dict[str, Any]:
    """Generate lesson completion trends chart"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Access control
        if tutor_id and current_user.role not in ["admin"] and current_user.id != tutor_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        chart_data = await chart_service.create_lesson_completion_chart(
            start_date, end_date, tutor_id, student_id, chart_type
        )
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating lesson completion chart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {str(e)}")

@router.get("/subjects/performance")
async def get_subject_performance_chart(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    chart_type: str = Query("bar", description="Chart type: bar, pie, scatter"),
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Dict[str, Any]:
    """Generate subject performance comparison chart"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Access control
        if tutor_id and current_user.role not in ["admin"] and current_user.id != tutor_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        chart_data = await chart_service.create_subject_performance_chart(
            start_date, end_date, tutor_id, chart_type
        )
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating subject performance chart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {str(e)}")

@router.get("/revenue/trends")
async def get_revenue_trends_chart(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    chart_type: str = Query("line", description="Chart type: line, bar"),
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Dict[str, Any]:
    """Generate revenue trends chart"""
    try:
        # Access control
        if current_user.role not in ["admin"] and (not tutor_id or current_user.id != tutor_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        chart_data = await chart_service.create_revenue_trends_chart(
            start_date, end_date, tutor_id, chart_type
        )
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating revenue trends chart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {str(e)}")

@router.get("/tutors/earnings")
async def get_tutor_earnings_chart(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    chart_type: str = Query("bar", description="Chart type: bar, pie, treemap"),
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Dict[str, Any]:
    """Generate tutor earnings comparison chart"""
    try:
        # Admin only endpoint
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        chart_data = await chart_service.create_tutor_earnings_chart(
            start_date, end_date, chart_type
        )
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating tutor earnings chart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {str(e)}")

@router.get("/users/activity")
async def get_user_activity_chart(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    chart_type: str = Query("line", description="Chart type: line, heatmap"),
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Dict[str, Any]:
    """Generate user activity trends chart"""
    try:
        # Admin only endpoint
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        chart_data = await chart_service.create_user_activity_chart(
            start_date, end_date, chart_type
        )
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating user activity chart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {str(e)}")

@router.get("/materials/usage")
async def get_material_usage_chart(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    chart_type: str = Query("bar", description="Chart type: bar, pie, treemap"),
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Dict[str, Any]:
    """Generate material usage chart"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        chart_data = await chart_service.create_material_usage_chart(
            start_date, end_date, chart_type
        )
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating material usage chart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {str(e)}")

@router.get("/dashboard/overview")
async def get_dashboard_overview_chart(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tutor_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Dict[str, Any]:
    """Generate comprehensive dashboard overview chart"""
    try:
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Access control
        if tutor_id and current_user.role not in ["admin"] and current_user.id != tutor_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        chart_data = await chart_service.create_dashboard_overview(
            start_date, end_date, tutor_id
        )
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error generating dashboard overview chart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chart: {str(e)}")

@router.post("/custom")
async def create_custom_chart(
    chart_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Dict[str, Any]:
    """Create custom chart from provided data and configuration"""
    try:
        data = chart_request.get("data", [])
        config = chart_request.get("config", {})
        
        if not data:
            raise HTTPException(status_code=400, detail="No data provided for custom chart")
        
        chart_data = await chart_service.create_custom_chart(data, config)
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error creating custom chart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create custom chart: {str(e)}")

@router.get("/export/{chart_type}")
async def export_chart_as_image(
    chart_type: str,
    chart_json: str = Query(..., description="Chart JSON data"),
    format: str = Query("png", description="Export format: png, jpeg, svg, pdf"),
    width: int = Query(800, description="Image width"),
    height: int = Query(600, description="Image height"),
    current_user: User = Depends(get_current_user),
    chart_service: ChartService = Depends(get_chart_service)
) -> Response:
    """Export chart as image file"""
    try:
        # Validate format
        valid_formats = ["png", "jpeg", "svg", "pdf"]
        if format.lower() not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Invalid format. Must be one of: {valid_formats}")
        
        # Export chart
        image_data = chart_service.export_chart_as_image(chart_json, format, width, height)
        
        # Set appropriate content type
        content_types = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "svg": "image/svg+xml",
            "pdf": "application/pdf"
        }
        
        # Create filename
        filename = f"{chart_type}_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        return Response(
            content=image_data,
            media_type=content_types[format.lower()],
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting chart as image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export chart: {str(e)}")

@router.get("/types")
async def get_available_chart_types(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get list of available chart types and their configurations"""
    try:
        chart_types = {
            "lesson_completion": {
                "types": ["line", "bar"],
                "description": "Lesson completion trends over time",
                "parameters": ["start_date", "end_date", "tutor_id", "student_id"]
            },
            "subject_performance": {
                "types": ["bar", "pie", "scatter"],
                "description": "Subject performance comparison",
                "parameters": ["start_date", "end_date", "tutor_id"]
            },
            "revenue_trends": {
                "types": ["line", "bar"],
                "description": "Revenue trends over time",
                "parameters": ["start_date", "end_date", "tutor_id"]
            },
            "tutor_earnings": {
                "types": ["bar", "pie", "treemap"],
                "description": "Tutor earnings comparison",
                "parameters": ["start_date", "end_date"]
            },
            "user_activity": {
                "types": ["line", "heatmap"],
                "description": "User activity trends",
                "parameters": ["start_date", "end_date"]
            },
            "material_usage": {
                "types": ["bar", "pie", "treemap"],
                "description": "Material usage statistics",
                "parameters": ["start_date", "end_date"]
            },
            "dashboard_overview": {
                "types": ["combined"],
                "description": "Comprehensive dashboard overview",
                "parameters": ["start_date", "end_date", "tutor_id"]
            }
        }
        
        # Filter chart types based on user role
        if current_user.role == "tutor":
            # Remove admin-only charts
            chart_types.pop("tutor_earnings", None)
            chart_types.pop("user_activity", None)
        elif current_user.role in ["parent", "student"]:
            # Limited chart access for parents/students
            allowed_charts = ["lesson_completion", "subject_performance", "material_usage"]
            chart_types = {k: v for k, v in chart_types.items() if k in allowed_charts}
        
        return {
            "chart_types": chart_types,
            "export_formats": ["png", "jpeg", "svg", "pdf"],
            "user_role": current_user.role
        }
        
    except Exception as e:
        logger.error(f"Error getting available chart types: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get chart types: {str(e)}")