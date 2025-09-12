"""
Chart Generation Service
Handles creation of interactive charts and visualizations using Plotly
"""

import json
import asyncio
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .lesson_analytics import LessonAnalyticsService
from .payment_analytics import PaymentAnalyticsService
from .user_analytics import UserAnalyticsService
from .material_analytics import MaterialAnalyticsService

logger = logging.getLogger(__name__)

class ChartService:
    """Service for generating charts and visualizations"""
    
    def __init__(self):
        self.lesson_service = LessonAnalyticsService()
        self.payment_service = PaymentAnalyticsService()
        self.user_service = UserAnalyticsService()
        self.material_service = MaterialAnalyticsService()
        
        # Configure Plotly defaults
        pio.templates.default = "plotly_white"
        self.color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]

    async def create_lesson_completion_chart(
        self,
        start_date: datetime,
        end_date: datetime,
        tutor_id: Optional[int] = None,
        student_id: Optional[int] = None,
        chart_type: str = "line"
    ) -> Dict[str, Any]:
        """Create lesson completion trends chart"""
        try:
            trends = await self.lesson_service.get_completion_trends(
                start_date, end_date, tutor_id, student_id
            )
            
            if not trends:
                return self._create_empty_chart("No lesson data available")
            
            df = pd.DataFrame(trends)
            df['date'] = pd.to_datetime(df['date'])
            
            if chart_type == "line":
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['completed_lessons'],
                    mode='lines+markers',
                    name='Completed Lessons',
                    line=dict(color=self.color_palette[0], width=3),
                    marker=dict(size=8)
                ))
                
                # Add completion rate on secondary y-axis
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['completion_rate'],
                    mode='lines+markers',
                    name='Completion Rate (%)',
                    yaxis='y2',
                    line=dict(color=self.color_palette[1], width=3),
                    marker=dict(size=8)
                ))
                
                fig.update_layout(
                    title='Lesson Completion Trends',
                    xaxis_title='Date',
                    yaxis=dict(title='Completed Lessons', side='left'),
                    yaxis2=dict(title='Completion Rate (%)', side='right', overlaying='y'),
                    hovermode='x unified',
                    template='plotly_white'
                )
                
            elif chart_type == "bar":
                fig = px.bar(
                    df, x='date', y='completed_lessons',
                    title='Lesson Completion by Date',
                    color='completion_rate',
                    color_continuous_scale='Viridis'
                )
                
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            return {
                'chart': fig.to_json(),
                'data': trends,
                'summary': {
                    'total_lessons': df['completed_lessons'].sum(),
                    'average_completion_rate': df['completion_rate'].mean(),
                    'peak_day': df.loc[df['completed_lessons'].idxmax(), 'date'].strftime('%Y-%m-%d')
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating lesson completion chart: {str(e)}")
            return self._create_error_chart(str(e))

    async def create_subject_performance_chart(
        self,
        start_date: datetime,
        end_date: datetime,
        tutor_id: Optional[int] = None,
        chart_type: str = "bar"
    ) -> Dict[str, Any]:
        """Create subject performance comparison chart"""
        try:
            performance = await self.lesson_service.get_subject_performance(
                start_date, end_date, tutor_id
            )
            
            if not performance:
                return self._create_empty_chart("No subject performance data available")
            
            df = pd.DataFrame(performance)
            
            if chart_type == "bar":
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('Total Lessons by Subject', 'Average Rating by Subject'),
                    vertical_spacing=0.1
                )
                
                # Total lessons bar chart
                fig.add_trace(
                    go.Bar(
                        x=df['subject_name'],
                        y=df['total_lessons'],
                        name='Total Lessons',
                        marker_color=self.color_palette[0]
                    ),
                    row=1, col=1
                )
                
                # Average rating bar chart
                fig.add_trace(
                    go.Bar(
                        x=df['subject_name'],
                        y=df['average_rating'],
                        name='Average Rating',
                        marker_color=self.color_palette[1]
                    ),
                    row=2, col=1
                )
                
                fig.update_layout(
                    title='Subject Performance Analysis',
                    showlegend=False,
                    height=600
                )
                
            elif chart_type == "pie":
                fig = px.pie(
                    df, values='total_lessons', names='subject_name',
                    title='Lesson Distribution by Subject',
                    color_discrete_sequence=self.color_palette
                )
                
            elif chart_type == "scatter":
                fig = px.scatter(
                    df, x='total_lessons', y='average_rating',
                    size='completion_rate', color='subject_name',
                    title='Subject Performance: Lessons vs Rating',
                    color_discrete_sequence=self.color_palette
                )
                
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            return {
                'chart': fig.to_json(),
                'data': performance,
                'summary': {
                    'total_subjects': len(df),
                    'most_popular_subject': df.loc[df['total_lessons'].idxmax(), 'subject_name'],
                    'highest_rated_subject': df.loc[df['average_rating'].idxmax(), 'subject_name']
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating subject performance chart: {str(e)}")
            return self._create_error_chart(str(e))

    async def create_revenue_trends_chart(
        self,
        start_date: datetime,
        end_date: datetime,
        tutor_id: Optional[int] = None,
        chart_type: str = "line"
    ) -> Dict[str, Any]:
        """Create revenue trends chart"""
        try:
            trends = await self.payment_service.get_revenue_trends(
                start_date, end_date, tutor_id
            )
            
            if not trends:
                return self._create_empty_chart("No revenue data available")
            
            df = pd.DataFrame(trends)
            df['date'] = pd.to_datetime(df['date'])
            
            if chart_type == "line":
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('Daily Revenue', 'Cumulative Revenue'),
                    vertical_spacing=0.1
                )
                
                # Daily revenue
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['revenue'],
                        mode='lines+markers',
                        name='Daily Revenue',
                        line=dict(color=self.color_palette[0], width=3),
                        marker=dict(size=6)
                    ),
                    row=1, col=1
                )
                
                # Cumulative revenue
                df['cumulative_revenue'] = df['revenue'].cumsum()
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['cumulative_revenue'],
                        mode='lines+markers',
                        name='Cumulative Revenue',
                        line=dict(color=self.color_palette[1], width=3),
                        marker=dict(size=6),
                        fill='tonexty'
                    ),
                    row=2, col=1
                )
                
                fig.update_layout(
                    title='Revenue Trends Analysis',
                    height=600,
                    showlegend=False
                )
                
            elif chart_type == "bar":
                fig = px.bar(
                    df, x='date', y='revenue',
                    title='Daily Revenue',
                    color='revenue',
                    color_continuous_scale='Blues'
                )
                
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            return {
                'chart': fig.to_json(),
                'data': trends,
                'summary': {
                    'total_revenue': df['revenue'].sum(),
                    'average_daily_revenue': df['revenue'].mean(),
                    'peak_revenue_day': df.loc[df['revenue'].idxmax(), 'date'].strftime('%Y-%m-%d'),
                    'peak_revenue_amount': df['revenue'].max()
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating revenue trends chart: {str(e)}")
            return self._create_error_chart(str(e))

    async def create_tutor_earnings_chart(
        self,
        start_date: datetime,
        end_date: datetime,
        chart_type: str = "bar"
    ) -> Dict[str, Any]:
        """Create tutor earnings comparison chart"""
        try:
            earnings = await self.payment_service.get_tutor_earnings(
                start_date, end_date
            )
            
            if not earnings:
                return self._create_empty_chart("No tutor earnings data available")
            
            df = pd.DataFrame(earnings)
            
            if chart_type == "bar":
                fig = px.bar(
                    df, x='tutor_name', y='total_earnings',
                    title='Tutor Earnings Comparison',
                    color='total_earnings',
                    color_continuous_scale='Greens'
                )
                fig.update_xaxis(tickangle=45)
                
            elif chart_type == "pie":
                fig = px.pie(
                    df, values='total_earnings', names='tutor_name',
                    title='Tutor Earnings Distribution',
                    color_discrete_sequence=self.color_palette
                )
                
            elif chart_type == "treemap":
                fig = px.treemap(
                    df, values='total_earnings', names='tutor_name',
                    title='Tutor Earnings Treemap',
                    color='total_earnings',
                    color_continuous_scale='RdYlGn'
                )
                
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            return {
                'chart': fig.to_json(),
                'data': earnings,
                'summary': {
                    'total_tutors': len(df),
                    'total_earnings': df['total_earnings'].sum(),
                    'average_earnings': df['total_earnings'].mean(),
                    'top_earner': df.loc[df['total_earnings'].idxmax(), 'tutor_name']
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating tutor earnings chart: {str(e)}")
            return self._create_error_chart(str(e))

    async def create_user_activity_chart(
        self,
        start_date: datetime,
        end_date: datetime,
        chart_type: str = "line"
    ) -> Dict[str, Any]:
        """Create user activity trends chart"""
        try:
            patterns = await self.user_service.get_login_patterns(
                start_date, end_date
            )
            
            if not patterns:
                return self._create_empty_chart("No user activity data available")
            
            df = pd.DataFrame(patterns)
            
            if chart_type == "line":
                fig = go.Figure()
                
                # Group by role if available
                if 'role' in df.columns:
                    for i, role in enumerate(df['role'].unique()):
                        role_data = df[df['role'] == role]
                        fig.add_trace(go.Scatter(
                            x=role_data['date'],
                            y=role_data['login_count'],
                            mode='lines+markers',
                            name=f'{role.title()} Logins',
                            line=dict(color=self.color_palette[i], width=3)
                        ))
                else:
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['login_count'],
                        mode='lines+markers',
                        name='Total Logins',
                        line=dict(color=self.color_palette[0], width=3)
                    ))
                
                fig.update_layout(
                    title='User Activity Trends',
                    xaxis_title='Date',
                    yaxis_title='Login Count',
                    hovermode='x unified'
                )
                
            elif chart_type == "heatmap":
                # Create hourly heatmap if hour data available
                if 'hour' in df.columns and 'day_of_week' in df.columns:
                    pivot_df = df.pivot_table(
                        values='login_count',
                        index='hour',
                        columns='day_of_week',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    fig = px.imshow(
                        pivot_df,
                        title='Login Activity Heatmap (Hour vs Day)',
                        labels=dict(x="Day of Week", y="Hour", color="Login Count"),
                        color_continuous_scale='Blues'
                    )
                else:
                    # Fallback to date-based heatmap
                    df['date'] = pd.to_datetime(df['date'])
                    df['day'] = df['date'].dt.day
                    df['month'] = df['date'].dt.month
                    
                    pivot_df = df.pivot_table(
                        values='login_count',
                        index='day',
                        columns='month',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    fig = px.imshow(
                        pivot_df,
                        title='Login Activity Heatmap (Day vs Month)',
                        labels=dict(x="Month", y="Day", color="Login Count"),
                        color_continuous_scale='Blues'
                    )
                    
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            return {
                'chart': fig.to_json(),
                'data': patterns,
                'summary': {
                    'total_logins': df['login_count'].sum() if 'login_count' in df.columns else 0,
                    'average_daily_logins': df['login_count'].mean() if 'login_count' in df.columns else 0,
                    'peak_activity_day': df.loc[df['login_count'].idxmax(), 'date'].strftime('%Y-%m-%d') if 'login_count' in df.columns and 'date' in df.columns else 'N/A'
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating user activity chart: {str(e)}")
            return self._create_error_chart(str(e))

    async def create_material_usage_chart(
        self,
        start_date: datetime,
        end_date: datetime,
        chart_type: str = "bar"
    ) -> Dict[str, Any]:
        """Create material usage chart"""
        try:
            popular_materials = await self.material_service.get_popular_materials(
                start_date, end_date
            )
            
            if not popular_materials:
                return self._create_empty_chart("No material usage data available")
            
            df = pd.DataFrame(popular_materials)
            
            if chart_type == "bar":
                fig = px.bar(
                    df.head(10), x='material_name', y='access_count',
                    title='Top 10 Most Accessed Materials',
                    color='access_count',
                    color_continuous_scale='Viridis'
                )
                fig.update_xaxis(tickangle=45)
                
            elif chart_type == "pie":
                fig = px.pie(
                    df.head(8), values='access_count', names='material_name',
                    title='Material Usage Distribution (Top 8)',
                    color_discrete_sequence=self.color_palette
                )
                
            elif chart_type == "treemap":
                fig = px.treemap(
                    df, values='access_count', names='material_name',
                    title='Material Usage Treemap',
                    color='access_count',
                    color_continuous_scale='Blues'
                )
                
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            return {
                'chart': fig.to_json(),
                'data': popular_materials,
                'summary': {
                    'total_materials': len(df),
                    'total_accesses': df['access_count'].sum(),
                    'most_popular_material': df.loc[df['access_count'].idxmax(), 'material_name']
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating material usage chart: {str(e)}")
            return self._create_error_chart(str(e))

    async def create_dashboard_overview(
        self,
        start_date: datetime,
        end_date: datetime,
        tutor_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create comprehensive dashboard with multiple charts"""
        try:
            # Create subplots for dashboard
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    'Lesson Completion Trends',
                    'Revenue Trends',
                    'User Activity',
                    'Subject Distribution'
                ),
                specs=[
                    [{"secondary_y": False}, {"secondary_y": False}],
                    [{"secondary_y": False}, {"type": "domain"}]
                ],
                vertical_spacing=0.1,
                horizontal_spacing=0.1
            )
            
            # Get data for all charts
            lesson_trends = await self.lesson_service.get_completion_trends(
                start_date, end_date, tutor_id
            )
            
            revenue_trends = await self.payment_service.get_revenue_trends(
                start_date, end_date, tutor_id
            )
            
            activity_patterns = await self.user_service.get_login_patterns(
                start_date, end_date
            )
            
            subject_performance = await self.lesson_service.get_subject_performance(
                start_date, end_date, tutor_id
            )
            
            # Add lesson completion trends
            if lesson_trends:
                lesson_df = pd.DataFrame(lesson_trends)
                fig.add_trace(
                    go.Scatter(
                        x=lesson_df['date'],
                        y=lesson_df['completed_lessons'],
                        mode='lines+markers',
                        name='Completed Lessons',
                        line=dict(color=self.color_palette[0])
                    ),
                    row=1, col=1
                )
            
            # Add revenue trends
            if revenue_trends:
                revenue_df = pd.DataFrame(revenue_trends)
                fig.add_trace(
                    go.Scatter(
                        x=revenue_df['date'],
                        y=revenue_df['revenue'],
                        mode='lines+markers',
                        name='Daily Revenue',
                        line=dict(color=self.color_palette[1])
                    ),
                    row=1, col=2
                )
            
            # Add user activity
            if activity_patterns:
                activity_df = pd.DataFrame(activity_patterns)
                fig.add_trace(
                    go.Scatter(
                        x=activity_df['date'],
                        y=activity_df.get('login_count', [0] * len(activity_df)),
                        mode='lines+markers',
                        name='User Logins',
                        line=dict(color=self.color_palette[2])
                    ),
                    row=2, col=1
                )
            
            # Add subject distribution
            if subject_performance:
                subject_df = pd.DataFrame(subject_performance)
                fig.add_trace(
                    go.Pie(
                        labels=subject_df['subject_name'],
                        values=subject_df['total_lessons'],
                        name="Subject Distribution"
                    ),
                    row=2, col=2
                )
            
            fig.update_layout(
                title='Analytics Dashboard Overview',
                height=800,
                showlegend=True
            )
            
            return {
                'chart': fig.to_json(),
                'summary': {
                    'lesson_trends_count': len(lesson_trends) if lesson_trends else 0,
                    'revenue_trends_count': len(revenue_trends) if revenue_trends else 0,
                    'activity_patterns_count': len(activity_patterns) if activity_patterns else 0,
                    'subjects_count': len(subject_performance) if subject_performance else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating dashboard overview: {str(e)}")
            return self._create_error_chart(str(e))

    async def create_custom_chart(
        self,
        data: List[Dict],
        chart_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create custom chart based on provided data and configuration"""
        try:
            if not data:
                return self._create_empty_chart("No data provided")
            
            df = pd.DataFrame(data)
            chart_type = chart_config.get('type', 'bar')
            x_column = chart_config.get('x', 'x')
            y_column = chart_config.get('y', 'y')
            title = chart_config.get('title', 'Custom Chart')
            
            if chart_type == 'bar':
                fig = px.bar(df, x=x_column, y=y_column, title=title)
            elif chart_type == 'line':
                fig = px.line(df, x=x_column, y=y_column, title=title)
            elif chart_type == 'scatter':
                fig = px.scatter(df, x=x_column, y=y_column, title=title)
            elif chart_type == 'pie':
                fig = px.pie(df, values=y_column, names=x_column, title=title)
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            return {
                'chart': fig.to_json(),
                'data': data,
                'config': chart_config
            }
            
        except Exception as e:
            logger.error(f"Error creating custom chart: {str(e)}")
            return self._create_error_chart(str(e))

    def _create_empty_chart(self, message: str) -> Dict[str, Any]:
        """Create empty chart with message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title="No Data Available",
            template="plotly_white"
        )
        
        return {
            'chart': fig.to_json(),
            'data': [],
            'message': message
        }

    def _create_error_chart(self, error_message: str) -> Dict[str, Any]:
        """Create error chart with error message"""
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {error_message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            title="Chart Generation Error",
            template="plotly_white"
        )
        
        return {
            'chart': fig.to_json(),
            'data': [],
            'error': error_message
        }

    @staticmethod
    def export_chart_as_image(chart_json: str, format: str = "png", width: int = 800, height: int = 600) -> bytes:
        """Export chart as image (PNG, JPEG, SVG, PDF)"""
        try:
            fig = go.Figure(json.loads(chart_json))
            
            if format.lower() == "png":
                return fig.to_image(format="png", width=width, height=height)
            elif format.lower() == "jpeg":
                return fig.to_image(format="jpeg", width=width, height=height)
            elif format.lower() == "svg":
                return fig.to_image(format="svg", width=width, height=height)
            elif format.lower() == "pdf":
                return fig.to_image(format="pdf", width=width, height=height)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting chart as image: {str(e)}")
            raise