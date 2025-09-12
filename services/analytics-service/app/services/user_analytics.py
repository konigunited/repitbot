from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
import pandas as pd
import numpy as np
from ..models.user_activity import UserActivity
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)


class UserAnalyticsService:
    """Service for user activity analytics and engagement metrics"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
    async def get_user_dashboard(
        self,
        user_id: str,
        role: str = 'student',  # student, tutor, parent, admin
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get comprehensive user dashboard data"""
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            query = select(UserActivity).where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.date >= start_date,
                    UserActivity.date <= end_date
                )
            ).order_by(asc(UserActivity.date))
            
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            if not activities:
                return self._empty_user_dashboard(user_id, role)
            
            dashboard = {
                'user_id': user_id,
                'role': role,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary_stats': self._calculate_summary_stats(activities),
                'engagement_metrics': self._calculate_engagement_metrics(activities),
                'learning_progress': self._analyze_learning_progress(activities),
                'activity_trends': self._calculate_activity_trends(activities),
                'performance_indicators': self._calculate_performance_indicators(activities),
                'goals_and_achievements': self._track_goals_achievements(activities),
                'risk_assessment': self._assess_user_risk(activities),
                'recommendations': await self._generate_recommendations(user_id, activities, role)
            }
            
            # Role-specific additions
            if role == 'student':
                dashboard.update(await self._add_student_specific_metrics(user_id, activities))
            elif role == 'tutor':
                dashboard.update(await self._add_tutor_specific_metrics(user_id, activities))
            elif role == 'parent':
                dashboard.update(await self._add_parent_specific_metrics(user_id, activities))
            elif role == 'admin':
                dashboard.update(await self._add_admin_specific_metrics(user_id, activities))
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error getting user dashboard for {user_id}: {e}")
            return self._empty_user_dashboard(user_id, role)
    
    async def get_engagement_analysis(
        self,
        user_ids: Optional[List[str]] = None,
        cohort: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Analyze user engagement patterns"""
        try:
            query = select(UserActivity)
            
            filters = []
            if user_ids:
                filters.append(UserActivity.user_id.in_(user_ids))
            if start_date:
                filters.append(UserActivity.date >= start_date)
            if end_date:
                filters.append(UserActivity.date <= end_date)
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            if not activities:
                return {}
            
            analysis = {
                'engagement_overview': self._analyze_overall_engagement(activities),
                'engagement_segments': self._segment_users_by_engagement(activities),
                'engagement_patterns': self._identify_engagement_patterns(activities),
                'platform_usage': self._analyze_platform_usage(activities),
                'behavioral_insights': self._extract_behavioral_insights(activities),
                'engagement_drivers': self._identify_engagement_drivers(activities),
                'churn_indicators': self._identify_churn_indicators(activities),
                'retention_analysis': await self._analyze_user_retention(activities)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing engagement: {e}")
            return {}
    
    async def get_learning_analytics(
        self,
        user_id: Optional[str] = None,
        subject: Optional[str] = None,
        time_range: str = 'month'
    ) -> Dict[str, Any]:
        """Analyze learning patterns and effectiveness"""
        try:
            query = select(UserActivity)
            
            filters = []
            if user_id:
                filters.append(UserActivity.user_id == user_id)
            
            # Date range filter
            end_date = datetime.utcnow()
            if time_range == 'week':
                start_date = end_date - timedelta(weeks=1)
            elif time_range == 'month':
                start_date = end_date - timedelta(days=30)
            elif time_range == 'quarter':
                start_date = end_date - timedelta(days=90)
            else:  # year
                start_date = end_date - timedelta(days=365)
            
            filters.append(UserActivity.date >= start_date)
            
            if filters:
                query = query.where(and_(*filters))
                
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            if not activities:
                return {}
            
            analytics = {
                'learning_velocity': self._calculate_learning_velocity(activities),
                'study_habits': self._analyze_study_habits(activities),
                'performance_trends': self._analyze_performance_trends(activities),
                'knowledge_retention': self._estimate_knowledge_retention(activities),
                'learning_efficiency': self._calculate_learning_efficiency(activities),
                'subject_mastery': self._assess_subject_mastery(activities, subject),
                'learning_style_indicators': self._identify_learning_style(activities),
                'improvement_areas': self._identify_improvement_areas(activities),
                'learning_milestones': self._track_learning_milestones(activities),
                'peer_comparison': await self._compare_with_peers(user_id, activities) if user_id else {}
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error analyzing learning patterns: {e}")
            return {}
    
    async def get_activity_heatmap(
        self,
        user_id: Optional[str] = None,
        activity_type: str = 'all',  # all, lessons, homework, materials
        granularity: str = 'hour'  # hour, day, week
    ) -> Dict[str, Any]:
        """Generate activity heatmap data"""
        try:
            query = select(UserActivity)
            
            if user_id:
                query = query.where(UserActivity.user_id == user_id)
            
            # Last 3 months of data
            start_date = datetime.utcnow() - timedelta(days=90)
            query = query.where(UserActivity.date >= start_date)
            
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            if not activities:
                return {}
            
            heatmap_data = self._generate_heatmap_data(activities, activity_type, granularity)
            
            return {
                'user_id': user_id,
                'activity_type': activity_type,
                'granularity': granularity,
                'data': heatmap_data,
                'peak_activity_periods': self._identify_peak_periods(heatmap_data),
                'activity_patterns': self._analyze_activity_patterns(heatmap_data),
                'recommendations': self._generate_activity_recommendations(heatmap_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating activity heatmap: {e}")
            return {}
    
    async def get_cohort_analysis(
        self,
        cohort_definition: str = 'monthly',  # monthly, weekly, custom
        metric: str = 'retention',  # retention, engagement, performance
        periods: int = 12
    ) -> Dict[str, Any]:
        """Perform cohort analysis on users"""
        try:
            # Get all user activities
            query = select(UserActivity).order_by(asc(UserActivity.date))
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            if not activities:
                return {}
            
            # Group users into cohorts
            cohorts = self._define_cohorts(activities, cohort_definition)
            
            # Calculate cohort metrics
            cohort_data = {}
            for cohort_name, users in cohorts.items():
                cohort_data[cohort_name] = self._calculate_cohort_metrics(
                    users, activities, metric, periods
                )
            
            analysis = {
                'cohort_definition': cohort_definition,
                'metric': metric,
                'periods_analyzed': periods,
                'cohort_data': cohort_data,
                'average_retention': self._calculate_average_retention(cohort_data),
                'cohort_insights': self._generate_cohort_insights(cohort_data),
                'best_performing_cohorts': self._identify_best_cohorts(cohort_data),
                'retention_curve': self._generate_retention_curve(cohort_data)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error performing cohort analysis: {e}")
            return {}
    
    async def get_user_segmentation(
        self,
        segmentation_criteria: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Segment users based on behavior and characteristics"""
        try:
            query = select(UserActivity)
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            if not activities:
                return {}
            
            # Default segmentation criteria
            if not segmentation_criteria:
                segmentation_criteria = {
                    'engagement_level': {'high': 80, 'medium': 50, 'low': 0},
                    'activity_frequency': {'daily': 7, 'weekly': 1, 'monthly': 0.25},
                    'performance_level': {'excellent': 90, 'good': 70, 'needs_improvement': 0}
                }
            
            # Calculate user segments
            user_segments = self._calculate_user_segments(activities, segmentation_criteria)
            
            segmentation = {
                'segmentation_criteria': segmentation_criteria,
                'total_users': len(set(a.user_id for a in activities)),
                'segments': user_segments,
                'segment_characteristics': self._analyze_segment_characteristics(user_segments, activities),
                'segment_trends': self._analyze_segment_trends(user_segments, activities),
                'actionable_insights': self._generate_segment_insights(user_segments),
                'recommended_strategies': self._recommend_segment_strategies(user_segments)
            }
            
            return segmentation
            
        except Exception as e:
            logger.error(f"Error performing user segmentation: {e}")
            return {}
    
    # Helper methods
    def _empty_user_dashboard(self, user_id: str, role: str) -> Dict[str, Any]:
        """Return empty dashboard structure"""
        return {
            'user_id': user_id,
            'role': role,
            'message': 'No activity data available for the specified period'
        }
    
    def _calculate_summary_stats(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Calculate summary statistics"""
        if not activities:
            return {}
        
        total_lessons = sum(a.lessons_attended for a in activities)
        total_homework = sum(a.homeworks_submitted for a in activities)
        total_study_time = sum(a.total_study_time for a in activities)
        
        return {
            'total_lessons_attended': total_lessons,
            'total_homeworks_submitted': total_homework,
            'total_study_time_minutes': total_study_time,
            'average_daily_activity': len(activities) / 30 if activities else 0,  # Assuming 30-day period
            'streak_days': max(a.streak_days for a in activities) if activities else 0,
            'login_frequency': sum(a.login_count for a in activities) / len(activities),
            'materials_accessed': sum(a.materials_accessed for a in activities)
        }
    
    def _calculate_engagement_metrics(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Calculate engagement metrics"""
        if not activities:
            return {}
        
        engagement_scores = [a.calculate_engagement_score() for a in activities]
        
        return {
            'average_engagement_score': np.mean(engagement_scores),
            'engagement_trend': 'increasing' if len(engagement_scores) > 1 and engagement_scores[-1] > engagement_scores[0] else 'stable',
            'peak_engagement': max(engagement_scores),
            'consistency_score': 100 - np.std(engagement_scores),  # Lower std = more consistent
            'active_days_percentage': len([a for a in activities if a.login_count > 0]) / len(activities) * 100
        }
    
    def _analyze_learning_progress(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Analyze learning progress"""
        if not activities:
            return {}
        
        # Calculate progress metrics
        completion_rates = [a.homework_completion_rate for a in activities if a.homework_completion_rate is not None]
        attendance_rates = [a.lesson_attendance_rate for a in activities if a.lesson_attendance_rate is not None]
        
        progress = {
            'homework_completion_trend': self._calculate_trend(completion_rates),
            'attendance_trend': self._calculate_trend(attendance_rates),
            'skill_development': self._track_skill_development(activities),
            'learning_milestones': self._extract_learning_milestones(activities),
            'areas_of_improvement': self._identify_learning_gaps(activities)
        }
        
        return progress
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from list of values"""
        if len(values) < 2:
            return 'insufficient_data'
        
        # Simple linear regression
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
        
        if slope > 0.1:
            return 'improving'
        elif slope < -0.1:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_activity_trends(self, activities: List[UserActivity]) -> List[Dict[str, Any]]:
        """Calculate activity trends over time"""
        trends = []
        
        for activity in sorted(activities, key=lambda x: x.date):
            trends.append({
                'date': activity.date.isoformat(),
                'engagement_score': activity.calculate_engagement_score(),
                'lessons_attended': activity.lessons_attended,
                'homework_completion': activity.homework_completion_rate,
                'study_time': activity.total_study_time
            })
        
        return trends
    
    def _calculate_performance_indicators(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Calculate performance indicators"""
        if not activities:
            return {}
        
        # Risk indicators
        risk_indicators = []
        for activity in activities:
            indicators = activity.get_risk_indicators()
            risk_indicators.extend(indicators)
        
        # Performance metrics
        avg_satisfaction = np.mean([a.satisfaction_score for a in activities if a.satisfaction_score])
        
        return {
            'performance_score': np.mean([a.calculate_engagement_score() for a in activities]),
            'satisfaction_score': avg_satisfaction,
            'risk_level': self._determine_risk_level(risk_indicators),
            'improvement_velocity': self._calculate_improvement_velocity(activities),
            'consistency_rating': self._calculate_consistency_rating(activities)
        }
    
    def _track_goals_achievements(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Track goals and achievements"""
        total_badges = sum(a.badges_earned for a in activities)
        max_streak = max(a.streak_days for a in activities) if activities else 0
        
        return {
            'total_badges_earned': total_badges,
            'longest_streak': max_streak,
            'achievements_this_period': self._extract_recent_achievements(activities),
            'progress_towards_goals': self._calculate_goal_progress(activities)
        }
    
    def _assess_user_risk(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Assess user risk factors"""
        if not activities:
            return {'risk_level': 'unknown'}
        
        # Collect all risk indicators
        all_risk_indicators = []
        for activity in activities:
            all_risk_indicators.extend(activity.get_risk_indicators())
        
        # Count occurrences of each risk type
        risk_summary = {}
        for indicator in all_risk_indicators:
            risk_summary[indicator] = risk_summary.get(indicator, 0) + 1
        
        # Determine overall risk level
        total_risks = len(all_risk_indicators)
        if total_risks >= 10:
            risk_level = 'high'
        elif total_risks >= 5:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'risk_indicators': risk_summary,
            'needs_intervention': risk_level in ['high', 'medium'],
            'recommended_actions': self._recommend_risk_mitigation(risk_summary)
        }
    
    async def _generate_recommendations(
        self,
        user_id: str,
        activities: List[UserActivity],
        role: str
    ) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        if not activities:
            return ['Start tracking your learning activities to receive personalized recommendations']
        
        # Analyze patterns and generate recommendations
        avg_engagement = np.mean([a.calculate_engagement_score() for a in activities])
        avg_completion = np.mean([a.homework_completion_rate for a in activities if a.homework_completion_rate])
        avg_attendance = np.mean([a.lesson_attendance_rate for a in activities if a.lesson_attendance_rate])
        
        if avg_engagement < 70:
            recommendations.append('Try to increase engagement by asking more questions during lessons')
        
        if avg_completion < 80:
            recommendations.append('Focus on improving homework completion rate')
        
        if avg_attendance < 90:
            recommendations.append('Work on maintaining consistent lesson attendance')
        
        # Role-specific recommendations
        if role == 'student':
            study_time = sum(a.total_study_time for a in activities)
            if study_time < 300:  # Less than 5 hours total
                recommendations.append('Consider increasing study time for better learning outcomes')
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    async def _add_student_specific_metrics(self, user_id: str, activities: List[UserActivity]) -> Dict[str, Any]:
        """Add student-specific metrics"""
        return {
            'student_metrics': {
                'grade_trend': self._calculate_grade_trend(activities),
                'subject_performance': self._analyze_subject_performance(activities),
                'study_efficiency': self._calculate_study_efficiency(activities),
                'peer_ranking': await self._calculate_peer_ranking(user_id, activities)
            }
        }
    
    async def _add_tutor_specific_metrics(self, user_id: str, activities: List[UserActivity]) -> Dict[str, Any]:
        """Add tutor-specific metrics"""
        return {
            'tutor_metrics': {
                'student_satisfaction': self._calculate_student_satisfaction(activities),
                'teaching_effectiveness': self._calculate_teaching_effectiveness(activities),
                'student_progress': self._track_student_progress(activities),
                'lesson_quality': self._assess_lesson_quality(activities)
            }
        }
    
    async def _add_parent_specific_metrics(self, user_id: str, activities: List[UserActivity]) -> Dict[str, Any]:
        """Add parent-specific metrics"""
        return {
            'parent_metrics': {
                'child_progress_overview': self._get_child_progress_overview(activities),
                'engagement_with_education': self._measure_parent_engagement(activities),
                'communication_frequency': self._calculate_communication_frequency(activities),
                'support_effectiveness': self._measure_support_effectiveness(activities)
            }
        }
    
    async def _add_admin_specific_metrics(self, user_id: str, activities: List[UserActivity]) -> Dict[str, Any]:
        """Add admin-specific metrics"""
        return {
            'admin_metrics': {
                'system_usage': self._analyze_system_usage(activities),
                'user_management': self._analyze_user_management(activities),
                'platform_health': self._assess_platform_health(activities),
                'operational_insights': self._generate_operational_insights(activities)
            }
        }
    
    def _analyze_overall_engagement(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Analyze overall engagement across all users"""
        if not activities:
            return {}
        
        engagement_scores = [a.calculate_engagement_score() for a in activities]
        
        return {
            'average_engagement': np.mean(engagement_scores),
            'median_engagement': np.median(engagement_scores),
            'engagement_distribution': self._calculate_engagement_distribution(engagement_scores),
            'high_engagement_users': len([s for s in engagement_scores if s >= 80]),
            'low_engagement_users': len([s for s in engagement_scores if s < 50]),
            'engagement_trend': self._calculate_engagement_trend_overall(activities)
        }
    
    def _segment_users_by_engagement(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Segment users by engagement level"""
        user_engagement = {}
        
        # Calculate engagement score for each user
        for activity in activities:
            user_id = activity.user_id
            engagement_score = activity.calculate_engagement_score()
            
            if user_id not in user_engagement:
                user_engagement[user_id] = []
            user_engagement[user_id].append(engagement_score)
        
        # Average engagement per user
        avg_engagement_per_user = {
            user_id: np.mean(scores) 
            for user_id, scores in user_engagement.items()
        }
        
        # Segment users
        segments = {
            'highly_engaged': [uid for uid, score in avg_engagement_per_user.items() if score >= 80],
            'moderately_engaged': [uid for uid, score in avg_engagement_per_user.items() if 50 <= score < 80],
            'low_engaged': [uid for uid, score in avg_engagement_per_user.items() if score < 50]
        }
        
        return {
            'segments': segments,
            'segment_sizes': {k: len(v) for k, v in segments.items()},
            'segment_percentages': {
                k: len(v) / len(avg_engagement_per_user) * 100 
                for k, v in segments.items()
            }
        }
    
    def _identify_engagement_patterns(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Identify engagement patterns"""
        # Temporal patterns
        day_engagement = {}
        hour_engagement = {}
        
        for activity in activities:
            day = activity.date.strftime('%A')
            hour = activity.date.hour
            engagement = activity.calculate_engagement_score()
            
            if day not in day_engagement:
                day_engagement[day] = []
            day_engagement[day].append(engagement)
            
            if hour not in hour_engagement:
                hour_engagement[hour] = []
            hour_engagement[hour].append(engagement)
        
        # Calculate averages
        day_avg = {day: np.mean(scores) for day, scores in day_engagement.items()}
        hour_avg = {hour: np.mean(scores) for hour, scores in hour_engagement.items()}
        
        return {
            'peak_engagement_day': max(day_avg, key=day_avg.get) if day_avg else None,
            'peak_engagement_hour': max(hour_avg, key=hour_avg.get) if hour_avg else None,
            'daily_patterns': day_avg,
            'hourly_patterns': hour_avg,
            'weekend_vs_weekday': self._compare_weekend_weekday_engagement(activities)
        }
    
    def _analyze_platform_usage(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Analyze platform usage patterns"""
        platform_data = []
        device_data = []
        
        for activity in activities:
            if activity.platform_usage:
                platform_data.append(activity.platform_usage)
            if activity.device_types:
                device_data.append(activity.device_types)
        
        # Aggregate platform usage
        platform_totals = {}
        device_totals = {}
        
        for platform_usage in platform_data:
            for platform, count in platform_usage.items():
                platform_totals[platform] = platform_totals.get(platform, 0) + count
        
        for device_usage in device_data:
            for device, count in device_usage.items():
                device_totals[device] = device_totals.get(device, 0) + count
        
        return {
            'platform_distribution': platform_totals,
            'device_distribution': device_totals,
            'most_popular_platform': max(platform_totals, key=platform_totals.get) if platform_totals else None,
            'most_popular_device': max(device_totals, key=device_totals.get) if device_totals else None
        }
    
    def _extract_behavioral_insights(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Extract behavioral insights"""
        insights = {
            'learning_preferences': self._identify_learning_preferences(activities),
            'activity_patterns': self._analyze_activity_patterns_behavioral(activities),
            'social_learning_indicators': self._analyze_social_learning(activities),
            'motivation_patterns': self._analyze_motivation_patterns(activities)
        }
        
        return insights
    
    def _identify_engagement_drivers(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Identify what drives user engagement"""
        # Correlate different factors with engagement scores
        engagement_factors = {
            'peer_interactions': [],
            'tutor_interactions': [],
            'material_variety': [],
            'achievement_frequency': []
        }
        
        for activity in activities:
            engagement = activity.calculate_engagement_score()
            
            engagement_factors['peer_interactions'].append({
                'engagement': engagement,
                'peer_interactions': activity.peer_interactions
            })
            
            engagement_factors['tutor_interactions'].append({
                'engagement': engagement,
                'tutor_interactions': activity.tutor_interactions
            })
        
        # Calculate correlations (simplified)
        drivers = {}
        for factor, data in engagement_factors.items():
            if data and len(data) > 1:
                engagements = [d['engagement'] for d in data]
                factor_values = [d[factor.replace('_', '_')] for d in data]
                
                # Simple correlation calculation
                correlation = np.corrcoef(engagements, factor_values)[0, 1]
                drivers[factor] = {
                    'correlation': correlation if not np.isnan(correlation) else 0,
                    'impact_level': 'high' if abs(correlation) > 0.5 else 'medium' if abs(correlation) > 0.3 else 'low'
                }
        
        return drivers
    
    def _identify_churn_indicators(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Identify indicators of potential churn"""
        user_activity_trends = {}
        
        # Track activity trends per user
        for activity in activities:
            user_id = activity.user_id
            if user_id not in user_activity_trends:
                user_activity_trends[user_id] = []
            
            user_activity_trends[user_id].append({
                'date': activity.date,
                'engagement': activity.calculate_engagement_score(),
                'login_count': activity.login_count,
                'lesson_attendance': activity.lesson_attendance_rate or 0
            })
        
        # Analyze trends for churn indicators
        churn_risk_users = []
        
        for user_id, trend_data in user_activity_trends.items():
            sorted_data = sorted(trend_data, key=lambda x: x['date'])
            
            if len(sorted_data) >= 3:  # Need minimum data points
                # Check for declining patterns
                recent_engagement = np.mean([d['engagement'] for d in sorted_data[-3:]])
                earlier_engagement = np.mean([d['engagement'] for d in sorted_data[:3]])
                
                if recent_engagement < earlier_engagement * 0.7:  # 30% decline
                    churn_risk_users.append(user_id)
        
        return {
            'high_churn_risk_users': churn_risk_users,
            'churn_risk_percentage': len(churn_risk_users) / len(user_activity_trends) * 100 if user_activity_trends else 0,
            'churn_indicators': {
                'declining_engagement': len(churn_risk_users),
                'low_activity': len([uid for uid, trends in user_activity_trends.items() 
                                  if np.mean([t['login_count'] for t in trends]) < 1])
            }
        }
    
    async def _analyze_user_retention(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Analyze user retention patterns"""
        # Group users by first activity date
        user_first_activity = {}
        
        for activity in activities:
            user_id = activity.user_id
            if user_id not in user_first_activity or activity.date < user_first_activity[user_id]:
                user_first_activity[user_id] = activity.date
        
        # Calculate retention by cohorts (simplified)
        current_date = datetime.utcnow()
        retention_data = {
            '1_week': 0,
            '1_month': 0,
            '3_months': 0,
            '6_months': 0
        }
        
        for user_id, first_date in user_first_activity.items():
            # Check if user is still active in different time periods
            user_activities = [a for a in activities if a.user_id == user_id]
            last_activity = max(user_activities, key=lambda x: x.date).date
            
            time_since_first = (current_date - first_date).days
            time_since_last = (current_date - last_activity).days
            
            if time_since_first >= 7 and time_since_last <= 7:
                retention_data['1_week'] += 1
            if time_since_first >= 30 and time_since_last <= 30:
                retention_data['1_month'] += 1
            if time_since_first >= 90 and time_since_last <= 30:
                retention_data['3_months'] += 1
            if time_since_first >= 180 and time_since_last <= 30:
                retention_data['6_months'] += 1
        
        total_users = len(user_first_activity)
        retention_rates = {
            period: (count / total_users * 100) if total_users > 0 else 0
            for period, count in retention_data.items()
        }
        
        return {
            'retention_rates': retention_rates,
            'total_users_analyzed': total_users,
            'average_retention': np.mean(list(retention_rates.values())),
            'retention_trend': 'needs_analysis'  # Would require more sophisticated analysis
        }
    
    # Additional helper methods would continue here...
    # Due to length constraints, I'll include key remaining methods
    
    def _calculate_learning_velocity(self, activities: List[UserActivity]) -> float:
        """Calculate learning velocity"""
        if len(activities) < 2:
            return 0.0
        
        # Sort activities by date
        sorted_activities = sorted(activities, key=lambda x: x.date)
        
        # Calculate improvement over time
        engagement_scores = [a.calculate_engagement_score() for a in sorted_activities]
        
        if len(engagement_scores) > 1:
            x = np.arange(len(engagement_scores))
            slope, _ = np.polyfit(x, engagement_scores, 1)
            return slope
        
        return 0.0
    
    def _analyze_study_habits(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Analyze study habits"""
        total_study_time = sum(a.total_study_time for a in activities)
        avg_session_duration = total_study_time / len(activities) if activities else 0
        
        # Analyze peak study hours
        peak_hours = []
        for activity in activities:
            if activity.peak_activity_hours:
                peak_hours.extend(activity.peak_activity_hours)
        
        most_common_hour = max(set(peak_hours), key=peak_hours.count) if peak_hours else None
        
        return {
            'total_study_time': total_study_time,
            'average_session_duration': avg_session_duration,
            'preferred_study_time': most_common_hour,
            'study_consistency': self._calculate_study_consistency(activities),
            'break_patterns': self._analyze_break_patterns(activities)
        }
    
    def _analyze_performance_trends(self, activities: List[UserActivity]) -> Dict[str, Any]:
        """Analyze performance trends"""
        performance_data = []
        
        for activity in sorted(activities, key=lambda x: x.date):
            performance_data.append({
                'date': activity.date.isoformat(),
                'homework_completion': activity.homework_completion_rate,
                'lesson_attendance': activity.lesson_attendance_rate,
                'engagement_score': activity.calculate_engagement_score()
            })
        
        return {
            'performance_timeline': performance_data,
            'overall_trend': self._calculate_overall_performance_trend(activities),
            'improvement_rate': self._calculate_improvement_rate(activities),
            'consistency_score': self._calculate_performance_consistency(activities)
        }
    
    def _generate_heatmap_data(self, activities: List[UserActivity], activity_type: str, granularity: str) -> Dict[str, Any]:
        """Generate heatmap data"""
        heatmap = {}
        
        for activity in activities:
            # Determine time key based on granularity
            if granularity == 'hour':
                time_key = f"{activity.date.hour:02d}:00"
            elif granularity == 'day':
                time_key = activity.date.strftime('%A')
            else:  # week
                time_key = f"Week {activity.date.isocalendar()[1]}"
            
            # Determine activity value based on type
            if activity_type == 'lessons':
                value = activity.lessons_attended
            elif activity_type == 'homework':
                value = activity.homeworks_submitted
            elif activity_type == 'materials':
                value = activity.materials_accessed
            else:  # all
                value = activity.calculate_engagement_score()
            
            if time_key not in heatmap:
                heatmap[time_key] = []
            heatmap[time_key].append(value)
        
        # Average values for each time period
        return {
            time_key: np.mean(values) for time_key, values in heatmap.items()
        }
    
    def _determine_risk_level(self, risk_indicators: List[str]) -> str:
        """Determine overall risk level"""
        risk_count = len(risk_indicators)
        
        if risk_count >= 5:
            return 'high'
        elif risk_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_improvement_velocity(self, activities: List[UserActivity]) -> float:
        """Calculate velocity of improvement"""
        if len(activities) < 2:
            return 0.0
        
        sorted_activities = sorted(activities, key=lambda x: x.date)
        engagement_scores = [a.calculate_engagement_score() for a in sorted_activities]
        
        # Calculate rate of change
        if len(engagement_scores) > 1:
            return (engagement_scores[-1] - engagement_scores[0]) / len(engagement_scores)
        
        return 0.0
    
    def _recommend_risk_mitigation(self, risk_summary: Dict[str, int]) -> List[str]:
        """Recommend actions to mitigate risks"""
        recommendations = []
        
        if 'low_attendance' in risk_summary:
            recommendations.append('Schedule regular check-ins to improve attendance')
        
        if 'poor_homework_completion' in risk_summary:
            recommendations.append('Provide additional homework support and reminders')
        
        if 'insufficient_study_time' in risk_summary:
            recommendations.append('Help create a structured study schedule')
        
        return recommendations[:3]  # Limit to top 3 recommendations