"""
Report Generation Service
Handles PDF/Excel report generation with templates and customization
"""

import io
import json
import asyncio
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader, select_autoescape
import xlswriter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from ..database import get_db
from ..models import User, Lesson, Payment, Homework, Material
from .lesson_analytics import LessonAnalyticsService
from .payment_analytics import PaymentAnalyticsService
from .user_analytics import UserAnalyticsService
from .material_analytics import MaterialAnalyticsService

logger = logging.getLogger(__name__)

class ReportService:
    """Service for generating various types of reports"""
    
    def __init__(self):
        self.lesson_service = LessonAnalyticsService()
        self.payment_service = PaymentAnalyticsService()
        self.user_service = UserAnalyticsService()
        self.material_service = MaterialAnalyticsService()
        
        # Setup Jinja2 environment
        self.template_dir = Path(__file__).parent.parent / "templates" / "reports"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Create default templates if they don't exist
        asyncio.create_task(self._create_default_templates())

    async def _create_default_templates(self):
        """Create default report templates"""
        templates = {
            'lesson_report.html': self._get_lesson_report_template(),
            'payment_report.html': self._get_payment_report_template(),
            'user_activity_report.html': self._get_user_activity_template(),
            'material_usage_report.html': self._get_material_usage_template(),
            'comprehensive_report.html': self._get_comprehensive_template()
        }
        
        for filename, content in templates.items():
            template_path = self.template_dir / filename
            if not template_path.exists():
                template_path.write_text(content, encoding='utf-8')

    async def generate_lesson_report(
        self,
        start_date: datetime,
        end_date: datetime,
        tutor_id: Optional[int] = None,
        student_id: Optional[int] = None,
        format: str = "pdf"
    ) -> bytes:
        """Generate lesson analytics report"""
        try:
            # Gather lesson data
            lesson_stats = await self.lesson_service.get_lesson_statistics(
                start_date, end_date, tutor_id, student_id
            )
            
            completion_trends = await self.lesson_service.get_completion_trends(
                start_date, end_date, tutor_id, student_id
            )
            
            subject_performance = await self.lesson_service.get_subject_performance(
                start_date, end_date, tutor_id, student_id
            )
            
            homework_stats = await self.lesson_service.get_homework_analytics(
                start_date, end_date, tutor_id, student_id
            )
            
            context = {
                'title': 'Lesson Analytics Report',
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'lesson_stats': lesson_stats,
                'completion_trends': completion_trends,
                'subject_performance': subject_performance,
                'homework_stats': homework_stats
            }
            
            if format.lower() == "pdf":
                return await self._generate_pdf_report('lesson_report.html', context)
            elif format.lower() == "excel":
                return await self._generate_excel_report('lesson', context)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error generating lesson report: {str(e)}")
            raise

    async def generate_payment_report(
        self,
        start_date: datetime,
        end_date: datetime,
        tutor_id: Optional[int] = None,
        format: str = "pdf"
    ) -> bytes:
        """Generate payment analytics report"""
        try:
            # Gather payment data
            payment_summary = await self.payment_service.get_payment_summary(
                start_date, end_date, tutor_id
            )
            
            revenue_trends = await self.payment_service.get_revenue_trends(
                start_date, end_date, tutor_id
            )
            
            tutor_earnings = await self.payment_service.get_tutor_earnings(
                start_date, end_date, tutor_id
            )
            
            payment_methods = await self.payment_service.get_payment_method_distribution(
                start_date, end_date, tutor_id
            )
            
            context = {
                'title': 'Payment Analytics Report',
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'payment_summary': payment_summary,
                'revenue_trends': revenue_trends,
                'tutor_earnings': tutor_earnings,
                'payment_methods': payment_methods
            }
            
            if format.lower() == "pdf":
                return await self._generate_pdf_report('payment_report.html', context)
            elif format.lower() == "excel":
                return await self._generate_excel_report('payment', context)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error generating payment report: {str(e)}")
            raise

    async def generate_user_activity_report(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "pdf"
    ) -> bytes:
        """Generate user activity report"""
        try:
            # Gather user activity data
            activity_summary = await self.user_service.get_activity_summary(
                start_date, end_date
            )
            
            login_patterns = await self.user_service.get_login_patterns(
                start_date, end_date
            )
            
            engagement_metrics = await self.user_service.get_engagement_metrics(
                start_date, end_date
            )
            
            role_distribution = await self.user_service.get_role_distribution()
            
            context = {
                'title': 'User Activity Report',
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'activity_summary': activity_summary,
                'login_patterns': login_patterns,
                'engagement_metrics': engagement_metrics,
                'role_distribution': role_distribution
            }
            
            if format.lower() == "pdf":
                return await self._generate_pdf_report('user_activity_report.html', context)
            elif format.lower() == "excel":
                return await self._generate_excel_report('user_activity', context)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error generating user activity report: {str(e)}")
            raise

    async def generate_material_usage_report(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "pdf"
    ) -> bytes:
        """Generate material usage report"""
        try:
            # Gather material usage data
            usage_summary = await self.material_service.get_usage_summary(
                start_date, end_date
            )
            
            popular_materials = await self.material_service.get_popular_materials(
                start_date, end_date
            )
            
            subject_distribution = await self.material_service.get_material_distribution_by_subject()
            
            upload_trends = await self.material_service.get_upload_trends(
                start_date, end_date
            )
            
            context = {
                'title': 'Material Usage Report',
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'usage_summary': usage_summary,
                'popular_materials': popular_materials,
                'subject_distribution': subject_distribution,
                'upload_trends': upload_trends
            }
            
            if format.lower() == "pdf":
                return await self._generate_pdf_report('material_usage_report.html', context)
            elif format.lower() == "excel":
                return await self._generate_excel_report('material_usage', context)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error generating material usage report: {str(e)}")
            raise

    async def generate_comprehensive_report(
        self,
        start_date: datetime,
        end_date: datetime,
        tutor_id: Optional[int] = None,
        format: str = "pdf"
    ) -> bytes:
        """Generate comprehensive analytics report combining all metrics"""
        try:
            # Gather data from all services
            lesson_stats = await self.lesson_service.get_lesson_statistics(
                start_date, end_date, tutor_id
            )
            
            payment_summary = await self.payment_service.get_payment_summary(
                start_date, end_date, tutor_id
            )
            
            activity_summary = await self.user_service.get_activity_summary(
                start_date, end_date
            )
            
            material_usage = await self.material_service.get_usage_summary(
                start_date, end_date
            )
            
            context = {
                'title': 'Comprehensive Analytics Report',
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'lesson_stats': lesson_stats,
                'payment_summary': payment_summary,
                'activity_summary': activity_summary,
                'material_usage': material_usage,
                'tutor_filter': tutor_id is not None
            }
            
            if format.lower() == "pdf":
                return await self._generate_pdf_report('comprehensive_report.html', context)
            elif format.lower() == "excel":
                return await self._generate_excel_report('comprehensive', context)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {str(e)}")
            raise

    async def _generate_pdf_report(self, template_name: str, context: Dict) -> bytes:
        """Generate PDF report from HTML template"""
        try:
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**context)
            
            # Create CSS for better PDF styling
            css_content = """
            @page {
                margin: 2cm;
                @top-center {
                    content: "{{ title }}";
                    font-size: 12px;
                    color: #666;
                }
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 10px;
                    color: #666;
                }
            }
            body {
                font-family: 'Arial', sans-serif;
                font-size: 12px;
                line-height: 1.4;
                color: #333;
            }
            .header {
                border-bottom: 2px solid #007bff;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            .metric-card {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin: 10px 0;
                background-color: #f9f9f9;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            """
            
            html_doc = HTML(string=html_content)
            css_doc = CSS(string=css_content)
            
            pdf_buffer = io.BytesIO()
            html_doc.write_pdf(pdf_buffer, stylesheets=[css_doc])
            
            return pdf_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            raise

    async def _generate_excel_report(self, report_type: str, context: Dict) -> bytes:
        """Generate Excel report with multiple sheets"""
        try:
            output = io.BytesIO()
            workbook = xlswriter.Workbook(output)
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4CAF50',
                'font_color': 'white',
                'align': 'center'
            })
            
            metric_format = workbook.add_format({
                'bg_color': '#E8F5E8',
                'align': 'center'
            })
            
            if report_type == 'lesson':
                await self._add_lesson_sheets(workbook, context, header_format, metric_format)
            elif report_type == 'payment':
                await self._add_payment_sheets(workbook, context, header_format, metric_format)
            elif report_type == 'user_activity':
                await self._add_user_activity_sheets(workbook, context, header_format, metric_format)
            elif report_type == 'material_usage':
                await self._add_material_usage_sheets(workbook, context, header_format, metric_format)
            elif report_type == 'comprehensive':
                await self._add_comprehensive_sheets(workbook, context, header_format, metric_format)
            
            workbook.close()
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating Excel report: {str(e)}")
            raise

    async def _add_lesson_sheets(self, workbook, context, header_format, metric_format):
        """Add lesson-related sheets to Excel workbook"""
        # Summary sheet
        summary_sheet = workbook.add_worksheet('Summary')
        stats = context['lesson_stats']
        
        summary_sheet.write(0, 0, 'Metric', header_format)
        summary_sheet.write(0, 1, 'Value', header_format)
        
        row = 1
        for key, value in stats.items():
            summary_sheet.write(row, 0, key.replace('_', ' ').title())
            summary_sheet.write(row, 1, value)
            row += 1
        
        # Trends sheet
        if 'completion_trends' in context:
            trends_sheet = workbook.add_worksheet('Completion Trends')
            trends = context['completion_trends']
            
            trends_sheet.write(0, 0, 'Date', header_format)
            trends_sheet.write(0, 1, 'Completed Lessons', header_format)
            trends_sheet.write(0, 2, 'Completion Rate (%)', header_format)
            
            for i, trend in enumerate(trends, 1):
                trends_sheet.write(i, 0, trend.get('date', ''))
                trends_sheet.write(i, 1, trend.get('completed_lessons', 0))
                trends_sheet.write(i, 2, trend.get('completion_rate', 0))

    async def _add_payment_sheets(self, workbook, context, header_format, metric_format):
        """Add payment-related sheets to Excel workbook"""
        # Summary sheet
        summary_sheet = workbook.add_worksheet('Payment Summary')
        summary = context['payment_summary']
        
        summary_sheet.write(0, 0, 'Metric', header_format)
        summary_sheet.write(0, 1, 'Value', header_format)
        
        row = 1
        for key, value in summary.items():
            summary_sheet.write(row, 0, key.replace('_', ' ').title())
            summary_sheet.write(row, 1, value)
            row += 1

    async def _add_user_activity_sheets(self, workbook, context, header_format, metric_format):
        """Add user activity sheets to Excel workbook"""
        # Activity Summary sheet
        activity_sheet = workbook.add_worksheet('Activity Summary')
        summary = context['activity_summary']
        
        activity_sheet.write(0, 0, 'Metric', header_format)
        activity_sheet.write(0, 1, 'Value', header_format)
        
        row = 1
        for key, value in summary.items():
            activity_sheet.write(row, 0, key.replace('_', ' ').title())
            activity_sheet.write(row, 1, value)
            row += 1

    async def _add_material_usage_sheets(self, workbook, context, header_format, metric_format):
        """Add material usage sheets to Excel workbook"""
        # Usage Summary sheet
        usage_sheet = workbook.add_worksheet('Usage Summary')
        summary = context['usage_summary']
        
        usage_sheet.write(0, 0, 'Metric', header_format)
        usage_sheet.write(0, 1, 'Value', header_format)
        
        row = 1
        for key, value in summary.items():
            usage_sheet.write(row, 0, key.replace('_', ' ').title())
            usage_sheet.write(row, 1, value)
            row += 1

    async def _add_comprehensive_sheets(self, workbook, context, header_format, metric_format):
        """Add comprehensive report sheets to Excel workbook"""
        # Overview sheet
        overview_sheet = workbook.add_worksheet('Overview')
        
        # Add summary from each service
        overview_sheet.write(0, 0, 'Service', header_format)
        overview_sheet.write(0, 1, 'Key Metrics', header_format)
        
        services = [
            ('Lessons', context.get('lesson_stats', {})),
            ('Payments', context.get('payment_summary', {})),
            ('User Activity', context.get('activity_summary', {})),
            ('Materials', context.get('material_usage', {}))
        ]
        
        row = 1
        for service_name, data in services:
            overview_sheet.write(row, 0, service_name)
            overview_sheet.write(row, 1, json.dumps(data, indent=2))
            row += 1

    def _get_lesson_report_template(self) -> str:
        """Default lesson report HTML template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p><strong>Period:</strong> {{ period }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
    </div>
    
    <div class="metric-card">
        <h2>Lesson Statistics</h2>
        {% for key, value in lesson_stats.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
    
    {% if completion_trends %}
    <div class="metric-card">
        <h2>Completion Trends</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Completed Lessons</th>
                    <th>Completion Rate (%)</th>
                </tr>
            </thead>
            <tbody>
                {% for trend in completion_trends %}
                <tr>
                    <td>{{ trend.date }}</td>
                    <td>{{ trend.completed_lessons }}</td>
                    <td>{{ trend.completion_rate }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
    
    {% if subject_performance %}
    <div class="metric-card">
        <h2>Subject Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Subject</th>
                    <th>Total Lessons</th>
                    <th>Completion Rate (%)</th>
                    <th>Average Rating</th>
                </tr>
            </thead>
            <tbody>
                {% for subject in subject_performance %}
                <tr>
                    <td>{{ subject.subject_name }}</td>
                    <td>{{ subject.total_lessons }}</td>
                    <td>{{ subject.completion_rate }}%</td>
                    <td>{{ subject.average_rating }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
</body>
</html>
        """

    def _get_payment_report_template(self) -> str:
        """Default payment report HTML template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p><strong>Period:</strong> {{ period }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
    </div>
    
    <div class="metric-card">
        <h2>Payment Summary</h2>
        {% for key, value in payment_summary.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
    
    {% if revenue_trends %}
    <div class="metric-card">
        <h2>Revenue Trends</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Revenue</th>
                    <th>Transactions</th>
                </tr>
            </thead>
            <tbody>
                {% for trend in revenue_trends %}
                <tr>
                    <td>{{ trend.date }}</td>
                    <td>${{ trend.revenue }}</td>
                    <td>{{ trend.transactions }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
</body>
</html>
        """

    def _get_user_activity_template(self) -> str:
        """Default user activity report HTML template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p><strong>Period:</strong> {{ period }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
    </div>
    
    <div class="metric-card">
        <h2>Activity Summary</h2>
        {% for key, value in activity_summary.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
</body>
</html>
        """

    def _get_material_usage_template(self) -> str:
        """Default material usage report HTML template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p><strong>Period:</strong> {{ period }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
    </div>
    
    <div class="metric-card">
        <h2>Usage Summary</h2>
        {% for key, value in usage_summary.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
</body>
</html>
        """

    def _get_comprehensive_template(self) -> str:
        """Default comprehensive report HTML template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p><strong>Period:</strong> {{ period }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
    </div>
    
    <div class="metric-card">
        <h2>Lesson Analytics</h2>
        {% for key, value in lesson_stats.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
    
    <div class="metric-card">
        <h2>Payment Analytics</h2>
        {% for key, value in payment_summary.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
    
    <div class="metric-card">
        <h2>User Activity</h2>
        {% for key, value in activity_summary.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
    
    <div class="metric-card">
        <h2>Material Usage</h2>
        {% for key, value in material_usage.items() %}
        <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
        {% endfor %}
    </div>
</body>
</html>
        """