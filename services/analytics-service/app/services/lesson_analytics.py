from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import pandas as pd
import numpy as np
from ..models.lesson_stats import LessonStats
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)


class LessonAnalyticsService:
    """Service for lesson analytics and statistics"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
    async def get_lesson_summary(
        self, 
        user_id: Optional[str] = None,
        tutor_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get comprehensive lesson summary statistics"""
        try:
            # Build base query
            query = select(LessonStats)
            
            # Apply filters
            filters = []
            if user_id:
                filters.append(LessonStats.student_id == user_id)
            if tutor_id:
                filters.append(LessonStats.tutor_id == tutor_id)
            if start_date:
                filters.append(LessonStats.date >= start_date)
            if end_date:
                filters.append(LessonStats.date <= end_date)
                
            if filters:
                query = query.where(and_(*filters))
            
            result = await self.db.execute(query)
            lessons = result.scalars().all()
            
            if not lessons:
                return self._empty_lesson_summary()
            
            # Calculate statistics
            summary = {
                'total_lessons': len(lessons),
                'completed_lessons': len([l for l in lessons if l.status == 'completed']),
                'cancelled_lessons': len([l for l in lessons if l.status == 'cancelled']),
                'missed_lessons': len([l for l in lessons if l.status == 'missed']),
                'average_duration': np.mean([l.duration_minutes for l in lessons if l.duration_minutes]),
                'average_completion_rate': np.mean([l.completion_rate for l in lessons if l.completion_rate]),
                'average_engagement': np.mean([l.engagement_score for l in lessons if l.engagement_score]),
                'total_study_time': sum(l.duration_minutes for l in lessons if l.duration_minutes),
                'attendance_rate': self._calculate_attendance_rate(lessons),
                'punctuality_score': np.mean([l.punctuality_score for l in lessons if l.punctuality_score]),
                'satisfaction_score': self._calculate_average_ratings(lessons),
                'top_subjects': self._get_top_subjects(lessons),
                'performance_trend': await self._calculate_performance_trend(lessons),
                'peak_learning_hours': self._get_peak_learning_hours(lessons)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting lesson summary: {e}")
            return self._empty_lesson_summary()
    
    async def get_tutor_performance(
        self,
        tutor_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get tutor performance analytics"""
        try:
            query = select(LessonStats).where(LessonStats.tutor_id == tutor_id)
            
            if start_date:
                query = query.where(LessonStats.date >= start_date)
            if end_date:
                query = query.where(LessonStats.date <= end_date)
            
            result = await self.db.execute(query)
            lessons = result.scalars().all()
            
            if not lessons:
                return {}
            
            performance = {
                'tutor_id': tutor_id,
                'total_lessons': len(lessons),
                'unique_students': len(set(l.student_id for l in lessons)),
                'average_student_rating': np.mean([l.student_rating for l in lessons if l.student_rating]),
                'average_parent_rating': np.mean([l.parent_rating for l in lessons if l.parent_rating]),
                'lesson_completion_rate': len([l for l in lessons if l.status == 'completed']) / len(lessons) * 100,
                'average_engagement_score': np.mean([l.engagement_score for l in lessons if l.engagement_score]),
                'punctuality_score': np.mean([l.punctuality_score for l in lessons if l.punctuality_score]),
                'technical_issues_rate': len([l for l in lessons if l.technical_issues]) / len(lessons) * 100,
                'student_questions_average': np.mean([l.student_questions for l in lessons]),
                'rescheduling_rate': len([l for l in lessons if l.was_rescheduled]) / len(lessons) * 100,
                'subjects_taught': list(set(l.subject for l in lessons if l.subject)),
                'best_performing_subjects': self._get_tutor_best_subjects(lessons),
                'improvement_areas': self._identify_tutor_improvement_areas(lessons),
                'monthly_trend': await self._get_tutor_monthly_trend(tutor_id, lessons)
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error getting tutor performance for {tutor_id}: {e}")
            return {}
    
    async def get_student_progress(
        self,
        student_id: str,
        subject: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get detailed student progress analytics"""
        try:
            query = select(LessonStats).where(LessonStats.student_id == student_id)
            
            if subject:
                query = query.where(LessonStats.subject == subject)
            if start_date:
                query = query.where(LessonStats.date >= start_date)
            if end_date:
                query = query.where(LessonStats.date <= end_date)
                
            query = query.order_by(asc(LessonStats.date))
            
            result = await self.db.execute(query)
            lessons = result.scalars().all()
            
            if not lessons:
                return {}
            
            progress = {
                'student_id': student_id,
                'total_lessons': len(lessons),
                'attendance_rate': self._calculate_attendance_rate(lessons),
                'average_performance': np.mean([l.get_performance_score() for l in lessons]),
                'skill_improvements': self._track_skill_improvements(lessons),
                'learning_velocity': self._calculate_learning_velocity(lessons),
                'consistency_score': self._calculate_consistency_score(lessons),
                'engagement_trend': self._calculate_engagement_trend(lessons),
                'weak_areas': self._identify_weak_areas(lessons),
                'strong_areas': self._identify_strong_areas(lessons),
                'recommended_focus': self._get_learning_recommendations(lessons),
                'milestone_progress': self._track_milestone_progress(lessons),
                'comparison_to_peers': await self._get_peer_comparison(student_id, lessons)
            }
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting student progress for {student_id}: {e}")
            return {}
    
    async def get_lesson_trends(
        self,
        period: str = 'month',  # day, week, month, quarter, year
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get lesson trends over time"""
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                if period == 'day':
                    start_date = end_date - timedelta(days=30)
                elif period == 'week':
                    start_date = end_date - timedelta(weeks=12)
                elif period == 'month':
                    start_date = end_date - timedelta(days=365)
                else:
                    start_date = end_date - timedelta(days=730)
            
            query = select(LessonStats).where(
                and_(
                    LessonStats.date >= start_date,
                    LessonStats.date <= end_date
                )
            ).order_by(asc(LessonStats.date))
            
            result = await self.db.execute(query)
            lessons = result.scalars().all()
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame([{
                'date': l.date,
                'status': l.status,
                'duration': l.duration_minutes,
                'rating': l.calculate_overall_rating(),
                'engagement': l.engagement_score,
                'subject': l.subject
            } for l in lessons])
            
            if df.empty:
                return {}
            
            # Group by period
            df['period'] = self._group_by_period(df['date'], period)
            
            trends = {
                'period_type': period,
                'total_periods': len(df['period'].unique()),
                'lessons_per_period': df.groupby('period').size().to_dict(),
                'completion_rate_trend': self._calculate_completion_trend(df),
                'engagement_trend': df.groupby('period')['engagement'].mean().to_dict(),
                'rating_trend': df.groupby('period')['rating'].mean().to_dict(),
                'duration_trend': df.groupby('period')['duration'].mean().to_dict(),
                'subject_popularity': df.groupby(['period', 'subject']).size().reset_index().to_dict(),
                'growth_rate': self._calculate_growth_rate(df, period),
                'seasonal_patterns': self._identify_seasonal_patterns(df),
                'predictions': await self._predict_future_trends(df, period)
            }
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting lesson trends: {e}")
            return {}
    
    async def get_curriculum_effectiveness(
        self,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze curriculum effectiveness"""
        try:
            query = select(LessonStats)
            
            filters = []
            if subject:
                filters.append(LessonStats.subject == subject)
            if grade_level:
                filters.append(LessonStats.grade_level == grade_level)
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await self.db.execute(query)
            lessons = result.scalars().all()
            
            if not lessons:
                return {}
            
            effectiveness = {
                'subject': subject,
                'grade_level': grade_level,
                'total_lessons_analyzed': len(lessons),
                'average_completion_rate': np.mean([l.completion_rate for l in lessons if l.completion_rate]),
                'learning_objective_success_rate': self._calculate_objective_success_rate(lessons),
                'student_satisfaction': np.mean([l.student_rating for l in lessons if l.student_rating]),
                'difficulty_appropriateness': self._analyze_difficulty_appropriateness(lessons),
                'engagement_by_topic': self._analyze_topic_engagement(lessons),
                'retention_indicators': self._calculate_retention_indicators(lessons),
                'improvement_recommendations': self._generate_curriculum_recommendations(lessons),
                'benchmark_comparison': await self._get_curriculum_benchmarks(subject, grade_level)
            }
            
            return effectiveness
            
        except Exception as e:
            logger.error(f"Error analyzing curriculum effectiveness: {e}")
            return {}
    
    # Helper methods
    def _empty_lesson_summary(self) -> Dict[str, Any]:
        """Return empty lesson summary structure"""
        return {
            'total_lessons': 0,
            'completed_lessons': 0,
            'cancelled_lessons': 0,
            'missed_lessons': 0,
            'average_duration': 0,
            'average_completion_rate': 0,
            'attendance_rate': 0,
            'satisfaction_score': 0
        }
    
    def _calculate_attendance_rate(self, lessons: List[LessonStats]) -> float:
        """Calculate attendance rate"""
        if not lessons:
            return 0.0
        
        present_lessons = len([l for l in lessons if l.attendance_status == 'present'])
        return (present_lessons / len(lessons)) * 100
    
    def _calculate_average_ratings(self, lessons: List[LessonStats]) -> float:
        """Calculate average satisfaction ratings"""
        ratings = []
        for lesson in lessons:
            overall_rating = lesson.calculate_overall_rating()
            if overall_rating > 0:
                ratings.append(overall_rating)
        
        return np.mean(ratings) if ratings else 0.0
    
    def _get_top_subjects(self, lessons: List[LessonStats]) -> List[Dict[str, Any]]:
        """Get top subjects by lesson count"""
        subjects = {}
        for lesson in lessons:
            if lesson.subject:
                if lesson.subject not in subjects:
                    subjects[lesson.subject] = {'count': 0, 'avg_rating': []}
                subjects[lesson.subject]['count'] += 1
                rating = lesson.calculate_overall_rating()
                if rating > 0:
                    subjects[lesson.subject]['avg_rating'].append(rating)
        
        # Calculate average ratings
        for subject in subjects:
            ratings = subjects[subject]['avg_rating']
            subjects[subject]['avg_rating'] = np.mean(ratings) if ratings else 0
        
        # Sort by count and return top 10
        sorted_subjects = sorted(subjects.items(), key=lambda x: x[1]['count'], reverse=True)
        return [
            {'subject': subject, 'count': data['count'], 'avg_rating': data['avg_rating']}
            for subject, data in sorted_subjects[:10]
        ]
    
    async def _calculate_performance_trend(self, lessons: List[LessonStats]) -> List[Dict[str, Any]]:
        """Calculate performance trend over time"""
        # Sort lessons by date
        sorted_lessons = sorted(lessons, key=lambda x: x.date)
        
        # Group by month and calculate average performance
        monthly_performance = {}
        for lesson in sorted_lessons:
            month_key = lesson.date.strftime('%Y-%m')
            if month_key not in monthly_performance:
                monthly_performance[month_key] = []
            
            performance_score = lesson.get_performance_score()
            monthly_performance[month_key].append(performance_score)
        
        # Calculate averages
        trend = []
        for month, scores in monthly_performance.items():
            trend.append({
                'period': month,
                'average_performance': np.mean(scores),
                'lesson_count': len(scores)
            })
        
        return sorted(trend, key=lambda x: x['period'])
    
    def _get_peak_learning_hours(self, lessons: List[LessonStats]) -> Dict[str, Any]:
        """Identify peak learning hours"""
        hour_distribution = {}
        for lesson in lessons:
            hour = lesson.date.hour
            if hour not in hour_distribution:
                hour_distribution[hour] = 0
            hour_distribution[hour] += 1
        
        if not hour_distribution:
            return {}
        
        peak_hour = max(hour_distribution, key=hour_distribution.get)
        return {
            'peak_hour': peak_hour,
            'lessons_at_peak': hour_distribution[peak_hour],
            'hourly_distribution': hour_distribution
        }
    
    def _get_tutor_best_subjects(self, lessons: List[LessonStats]) -> List[Dict[str, Any]]:
        """Get tutor's best performing subjects"""
        subject_performance = {}
        
        for lesson in lessons:
            if not lesson.subject:
                continue
                
            if lesson.subject not in subject_performance:
                subject_performance[lesson.subject] = {
                    'ratings': [],
                    'engagement_scores': [],
                    'completion_rates': []
                }
            
            if lesson.student_rating:
                subject_performance[lesson.subject]['ratings'].append(lesson.student_rating)
            if lesson.engagement_score:
                subject_performance[lesson.subject]['engagement_scores'].append(lesson.engagement_score)
            if lesson.completion_rate:
                subject_performance[lesson.subject]['completion_rates'].append(lesson.completion_rate)
        
        # Calculate averages and sort
        performance_list = []
        for subject, metrics in subject_performance.items():
            avg_rating = np.mean(metrics['ratings']) if metrics['ratings'] else 0
            avg_engagement = np.mean(metrics['engagement_scores']) if metrics['engagement_scores'] else 0
            avg_completion = np.mean(metrics['completion_rates']) if metrics['completion_rates'] else 0
            
            overall_score = (avg_rating * 0.4 + avg_engagement * 0.4 + avg_completion * 0.2)
            
            performance_list.append({
                'subject': subject,
                'overall_score': overall_score,
                'avg_rating': avg_rating,
                'avg_engagement': avg_engagement,
                'avg_completion': avg_completion,
                'lesson_count': len(metrics['ratings'] + metrics['engagement_scores'] + metrics['completion_rates']) / 3
            })
        
        return sorted(performance_list, key=lambda x: x['overall_score'], reverse=True)[:5]
    
    def _identify_tutor_improvement_areas(self, lessons: List[LessonStats]) -> List[str]:
        """Identify areas where tutor could improve"""
        improvements = []
        
        # Calculate averages
        avg_punctuality = np.mean([l.punctuality_score for l in lessons if l.punctuality_score])
        avg_engagement = np.mean([l.engagement_score for l in lessons if l.engagement_score])
        avg_rating = np.mean([l.student_rating for l in lessons if l.student_rating])
        technical_issues_rate = len([l for l in lessons if l.technical_issues]) / len(lessons)
        reschedule_rate = len([l for l in lessons if l.was_rescheduled]) / len(lessons)
        
        if avg_punctuality < 4.0:
            improvements.append('punctuality')
        if avg_engagement < 3.5:
            improvements.append('student_engagement')
        if avg_rating < 4.0:
            improvements.append('lesson_quality')
        if technical_issues_rate > 0.2:
            improvements.append('technical_preparation')
        if reschedule_rate > 0.15:
            improvements.append('schedule_reliability')
        
        return improvements
    
    async def _get_tutor_monthly_trend(self, tutor_id: str, lessons: List[LessonStats]) -> List[Dict[str, Any]]:
        """Get tutor's monthly performance trend"""
        monthly_data = {}
        
        for lesson in lessons:
            month_key = lesson.date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'lesson_count': 0,
                    'ratings': [],
                    'engagement_scores': []
                }
            
            monthly_data[month_key]['lesson_count'] += 1
            if lesson.student_rating:
                monthly_data[month_key]['ratings'].append(lesson.student_rating)
            if lesson.engagement_score:
                monthly_data[month_key]['engagement_scores'].append(lesson.engagement_score)
        
        trend = []
        for month, data in monthly_data.items():
            trend.append({
                'month': month,
                'lesson_count': data['lesson_count'],
                'avg_rating': np.mean(data['ratings']) if data['ratings'] else 0,
                'avg_engagement': np.mean(data['engagement_scores']) if data['engagement_scores'] else 0
            })
        
        return sorted(trend, key=lambda x: x['month'])
    
    def _track_skill_improvements(self, lessons: List[LessonStats]) -> Dict[str, Any]:
        """Track skill improvements over time"""
        # This would typically involve analyzing lesson objectives and outcomes
        improvements = {}
        
        for lesson in lessons:
            if lesson.learning_objectives_met:
                for objective in lesson.learning_objectives_met:
                    if objective not in improvements:
                        improvements[objective] = {'count': 0, 'dates': []}
                    improvements[objective]['count'] += 1
                    improvements[objective]['dates'].append(lesson.date)
        
        # Calculate improvement velocity for each skill
        for skill, data in improvements.items():
            dates = sorted(data['dates'])
            if len(dates) > 1:
                days_between = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
                improvements[skill]['avg_days_between'] = np.mean(days_between)
            else:
                improvements[skill]['avg_days_between'] = None
        
        return improvements
    
    def _calculate_learning_velocity(self, lessons: List[LessonStats]) -> float:
        """Calculate learning velocity (progress per unit time)"""
        if len(lessons) < 2:
            return 0.0
        
        sorted_lessons = sorted(lessons, key=lambda x: x.date)
        
        # Calculate cumulative performance scores
        performance_scores = [lesson.get_performance_score() for lesson in sorted_lessons]
        
        # Simple linear regression to find velocity
        if len(performance_scores) > 1:
            x = np.arange(len(performance_scores))
            slope, _ = np.polyfit(x, performance_scores, 1)
            return slope
        
        return 0.0
    
    def _calculate_consistency_score(self, lessons: List[LessonStats]) -> float:
        """Calculate consistency of performance"""
        performance_scores = [lesson.get_performance_score() for lesson in lessons]
        
        if not performance_scores:
            return 0.0
        
        # Lower standard deviation = higher consistency
        std_dev = np.std(performance_scores)
        mean_score = np.mean(performance_scores)
        
        # Normalize consistency score (0-100)
        if mean_score > 0:
            consistency = max(0, 100 - (std_dev / mean_score * 100))
        else:
            consistency = 0
        
        return consistency
    
    def _calculate_engagement_trend(self, lessons: List[LessonStats]) -> List[Dict[str, Any]]:
        """Calculate engagement trend over time"""
        sorted_lessons = sorted(lessons, key=lambda x: x.date)
        
        trend = []
        for lesson in sorted_lessons:
            trend.append({
                'date': lesson.date.isoformat(),
                'engagement_score': lesson.engagement_score or 0,
                'questions_asked': lesson.student_questions or 0
            })
        
        return trend
    
    def _identify_weak_areas(self, lessons: List[LessonStats]) -> List[Dict[str, Any]]:
        """Identify areas where student struggles"""
        weak_areas = []
        
        # Analyze by subject
        subject_performance = {}
        for lesson in lessons:
            if lesson.subject:
                if lesson.subject not in subject_performance:
                    subject_performance[lesson.subject] = []
                subject_performance[lesson.subject].append(lesson.get_performance_score())
        
        for subject, scores in subject_performance.items():
            avg_score = np.mean(scores)
            if avg_score < 70:  # Below 70% performance
                weak_areas.append({
                    'area': subject,
                    'type': 'subject',
                    'avg_performance': avg_score,
                    'lesson_count': len(scores)
                })
        
        return weak_areas
    
    def _identify_strong_areas(self, lessons: List[LessonStats]) -> List[Dict[str, Any]]:
        """Identify areas where student excels"""
        strong_areas = []
        
        # Analyze by subject
        subject_performance = {}
        for lesson in lessons:
            if lesson.subject:
                if lesson.subject not in subject_performance:
                    subject_performance[lesson.subject] = []
                subject_performance[lesson.subject].append(lesson.get_performance_score())
        
        for subject, scores in subject_performance.items():
            avg_score = np.mean(scores)
            if avg_score >= 85:  # Above 85% performance
                strong_areas.append({
                    'area': subject,
                    'type': 'subject',
                    'avg_performance': avg_score,
                    'lesson_count': len(scores)
                })
        
        return strong_areas
    
    def _get_learning_recommendations(self, lessons: List[LessonStats]) -> List[str]:
        """Generate learning recommendations based on patterns"""
        recommendations = []
        
        # Analyze patterns
        weak_areas = self._identify_weak_areas(lessons)
        consistency_score = self._calculate_consistency_score(lessons)
        attendance_rate = self._calculate_attendance_rate(lessons)
        avg_engagement = np.mean([l.engagement_score for l in lessons if l.engagement_score])
        
        if weak_areas:
            recommendations.append(f"Focus on improving {weak_areas[0]['area']} - consider additional practice")
        
        if consistency_score < 70:
            recommendations.append("Work on maintaining consistent performance across lessons")
        
        if attendance_rate < 90:
            recommendations.append("Improve attendance rate to maximize learning opportunities")
        
        if avg_engagement and avg_engagement < 4:
            recommendations.append("Increase engagement through interactive activities and questions")
        
        return recommendations
    
    def _track_milestone_progress(self, lessons: List[LessonStats]) -> Dict[str, Any]:
        """Track milestone progress"""
        milestones = {}
        
        for lesson in lessons:
            if lesson.progress_milestones:
                for milestone in lesson.progress_milestones:
                    if milestone not in milestones:
                        milestones[milestone] = {'achieved_date': lesson.date, 'lesson_count': 0}
                    milestones[milestone]['lesson_count'] += 1
        
        return milestones
    
    async def _get_peer_comparison(self, student_id: str, lessons: List[LessonStats]) -> Dict[str, Any]:
        """Compare student performance to peers"""
        # This would typically query for similar students (same grade, subject, etc.)
        # For now, return a placeholder structure
        return {
            'percentile_rank': 0,
            'compared_to': 0,
            'better_than_percent': 0,
            'areas_above_average': [],
            'areas_below_average': []
        }
    
    def _group_by_period(self, dates: pd.Series, period: str) -> pd.Series:
        """Group dates by specified period"""
        if period == 'day':
            return dates.dt.strftime('%Y-%m-%d')
        elif period == 'week':
            return dates.dt.strftime('%Y-W%U')
        elif period == 'month':
            return dates.dt.strftime('%Y-%m')
        elif period == 'quarter':
            return dates.dt.to_period('Q').astype(str)
        else:  # year
            return dates.dt.strftime('%Y')
    
    def _calculate_completion_trend(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate completion rate trend by period"""
        completion_by_period = df[df['status'] == 'completed'].groupby('period').size()
        total_by_period = df.groupby('period').size()
        
        completion_rates = (completion_by_period / total_by_period * 100).fillna(0)
        return completion_rates.to_dict()
    
    def _calculate_growth_rate(self, df: pd.DataFrame, period: str) -> float:
        """Calculate growth rate over the period"""
        lesson_counts = df.groupby('period').size().sort_index()
        
        if len(lesson_counts) < 2:
            return 0.0
        
        first_period_count = lesson_counts.iloc[0]
        last_period_count = lesson_counts.iloc[-1]
        
        if first_period_count == 0:
            return 0.0
        
        growth_rate = ((last_period_count - first_period_count) / first_period_count) * 100
        return growth_rate
    
    def _identify_seasonal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify seasonal patterns in lesson data"""
        # This would analyze monthly/quarterly patterns
        # For now, return basic day-of-week patterns
        if 'date' in df.columns:
            df['day_of_week'] = pd.to_datetime(df['date']).dt.day_name()
            day_distribution = df['day_of_week'].value_counts().to_dict()
            
            return {
                'day_of_week_distribution': day_distribution,
                'most_active_day': max(day_distribution, key=day_distribution.get),
                'least_active_day': min(day_distribution, key=day_distribution.get)
            }
        
        return {}
    
    async def _predict_future_trends(self, df: pd.DataFrame, period: str) -> Dict[str, Any]:
        """Simple trend prediction based on historical data"""
        # This would typically use more sophisticated ML models
        # For now, return simple linear projections
        
        lesson_counts = df.groupby('period').size().sort_index()
        
        if len(lesson_counts) < 3:
            return {'prediction_available': False}
        
        # Simple linear regression for prediction
        x = np.arange(len(lesson_counts))
        y = lesson_counts.values
        
        slope, intercept = np.polyfit(x, y, 1)
        
        # Predict next 3 periods
        future_periods = 3
        future_x = np.arange(len(lesson_counts), len(lesson_counts) + future_periods)
        predictions = slope * future_x + intercept
        
        return {
            'prediction_available': True,
            'trend_direction': 'increasing' if slope > 0 else 'decreasing',
            'predicted_counts': predictions.tolist(),
            'confidence': 'low'  # Would be calculated in real implementation
        }
    
    def _calculate_objective_success_rate(self, lessons: List[LessonStats]) -> float:
        """Calculate learning objective success rate"""
        total_objectives = 0
        met_objectives = 0
        
        for lesson in lessons:
            if lesson.learning_objectives_met:
                met_objectives += len(lesson.learning_objectives_met)
            # Assume 3 objectives per lesson if not specified
            total_objectives += 3
        
        if total_objectives == 0:
            return 0.0
        
        return (met_objectives / total_objectives) * 100
    
    def _analyze_difficulty_appropriateness(self, lessons: List[LessonStats]) -> Dict[str, Any]:
        """Analyze if difficulty levels are appropriate"""
        difficulty_ratings = [l.difficulty_rating for l in lessons if l.difficulty_rating]
        
        if not difficulty_ratings:
            return {'analysis_available': False}
        
        avg_difficulty = np.mean(difficulty_ratings)
        difficulty_distribution = {}
        
        for rating in difficulty_ratings:
            if rating <= 2:
                key = 'too_easy'
            elif rating >= 4:
                key = 'too_hard'
            else:
                key = 'appropriate'
            
            difficulty_distribution[key] = difficulty_distribution.get(key, 0) + 1
        
        return {
            'analysis_available': True,
            'average_difficulty': avg_difficulty,
            'distribution': difficulty_distribution,
            'recommendation': self._get_difficulty_recommendation(avg_difficulty, difficulty_distribution)
        }
    
    def _get_difficulty_recommendation(self, avg_difficulty: float, distribution: Dict[str, int]) -> str:
        """Get difficulty adjustment recommendation"""
        if avg_difficulty < 2.5:
            return "Consider increasing difficulty level"
        elif avg_difficulty > 3.5:
            return "Consider reducing difficulty level"
        elif distribution.get('appropriate', 0) < len(distribution) * 0.6:
            return "Review and adjust difficulty for individual lessons"
        else:
            return "Difficulty level is well-balanced"
    
    def _analyze_topic_engagement(self, lessons: List[LessonStats]) -> Dict[str, float]:
        """Analyze engagement by topic"""
        topic_engagement = {}
        
        for lesson in lessons:
            if lesson.topics_covered and lesson.engagement_score:
                for topic in lesson.topics_covered:
                    if topic not in topic_engagement:
                        topic_engagement[topic] = []
                    topic_engagement[topic].append(lesson.engagement_score)
        
        # Calculate average engagement per topic
        for topic, scores in topic_engagement.items():
            topic_engagement[topic] = np.mean(scores)
        
        return topic_engagement
    
    def _calculate_retention_indicators(self, lessons: List[LessonStats]) -> Dict[str, Any]:
        """Calculate retention indicators"""
        # This would analyze homework completion after lessons, quiz scores, etc.
        retention_data = {
            'homework_completion_rate': 0,
            'quiz_improvement_rate': 0,
            'topic_retention_scores': {},
            'long_term_retention': 0
        }
        
        homework_completion = []
        for lesson in lessons:
            if hasattr(lesson, 'homework_completion_previous') and lesson.homework_completion_previous is not None:
                homework_completion.append(lesson.homework_completion_previous)
        
        if homework_completion:
            retention_data['homework_completion_rate'] = sum(homework_completion) / len(homework_completion) * 100
        
        return retention_data
    
    def _generate_curriculum_recommendations(self, lessons: List[LessonStats]) -> List[str]:
        """Generate curriculum improvement recommendations"""
        recommendations = []
        
        avg_completion = np.mean([l.completion_rate for l in lessons if l.completion_rate])
        avg_engagement = np.mean([l.engagement_score for l in lessons if l.engagement_score])
        avg_rating = np.mean([l.calculate_overall_rating() for l in lessons])
        
        if avg_completion < 80:
            recommendations.append("Review lesson pacing - completion rates are below optimal")
        
        if avg_engagement < 3.5:
            recommendations.append("Incorporate more interactive elements to boost engagement")
        
        if avg_rating < 4:
            recommendations.append("Review lesson content quality and teaching methods")
        
        # Analyze topic-specific issues
        topic_engagement = self._analyze_topic_engagement(lessons)
        low_engagement_topics = [topic for topic, score in topic_engagement.items() if score < 3]
        
        if low_engagement_topics:
            recommendations.append(f"Review content for topics with low engagement: {', '.join(low_engagement_topics[:3])}")
        
        return recommendations
    
    async def _get_curriculum_benchmarks(self, subject: Optional[str], grade_level: Optional[str]) -> Dict[str, Any]:
        """Get curriculum benchmarks for comparison"""
        # This would typically query industry benchmarks or historical data
        # For now, return placeholder benchmark data
        return {
            'industry_avg_completion_rate': 85.0,
            'industry_avg_satisfaction': 4.2,
            'industry_avg_engagement': 3.8,
            'benchmark_source': 'internal_historical',
            'comparison_available': True
        }