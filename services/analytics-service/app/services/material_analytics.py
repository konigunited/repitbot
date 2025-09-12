from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
import pandas as pd
import numpy as np
from ..models.material_usage import MaterialUsage
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)


class MaterialAnalyticsService:
    """Service for material usage analytics and content effectiveness"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
    async def get_material_performance(
        self,
        material_id: Optional[str] = None,
        material_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get comprehensive material performance analytics"""
        try:
            query = select(MaterialUsage)
            
            filters = []
            if material_id:
                filters.append(MaterialUsage.material_id == material_id)
            if material_type:
                filters.append(MaterialUsage.material_type == material_type)
            if start_date:
                filters.append(MaterialUsage.access_date >= start_date)
            if end_date:
                filters.append(MaterialUsage.access_date <= end_date)
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await self.db.execute(query)
            usages = result.scalars().all()
            
            if not usages:
                return self._empty_material_performance()
            
            performance = {
                'material_overview': self._calculate_material_overview(usages),
                'engagement_metrics': self._calculate_material_engagement(usages),
                'completion_analytics': self._analyze_completion_patterns(usages),
                'effectiveness_scores': self._calculate_effectiveness_scores(usages),
                'user_feedback': self._analyze_user_feedback(usages),
                'usage_patterns': self._identify_usage_patterns(usages),
                'learning_outcomes': await self._assess_learning_outcomes(usages),
                'content_optimization': self._generate_content_recommendations(usages),
                'comparative_analysis': await self._compare_material_performance(usages)
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error getting material performance: {e}")
            return self._empty_material_performance()
    
    async def get_content_analytics(
        self,
        category: Optional[str] = None,
        subject: Optional[str] = None,
        difficulty_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze content performance across categories"""
        try:
            query = select(MaterialUsage)
            
            filters = []
            if category:
                filters.append(MaterialUsage.material_category == category)
            if subject:
                filters.append(MaterialUsage.subject == subject)
            if difficulty_level:
                filters.append(MaterialUsage.difficulty_level == difficulty_level)
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await self.db.execute(query)
            usages = result.scalars().all()
            
            if not usages:
                return {}
            
            analytics = {
                'content_overview': self._analyze_content_overview(usages),
                'popularity_rankings': self._rank_content_popularity(usages),
                'engagement_by_type': self._analyze_engagement_by_type(usages),
                'completion_rates': self._analyze_completion_rates_by_category(usages),
                'difficulty_effectiveness': self._analyze_difficulty_effectiveness(usages),
                'content_gaps': self._identify_content_gaps(usages),
                'trending_content': self._identify_trending_content(usages),
                'content_lifecycle': self._analyze_content_lifecycle(usages),
                'personalization_insights': self._generate_personalization_insights(usages)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return {}
    
    async def get_usage_heatmap(
        self,
        time_granularity: str = 'hour',  # hour, day, week, month
        user_segment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate material usage heatmap"""
        try:
            query = select(MaterialUsage)
            
            # Last 90 days of data
            start_date = datetime.utcnow() - timedelta(days=90)
            query = query.where(MaterialUsage.access_date >= start_date)
            
            result = await self.db.execute(query)
            usages = result.scalars().all()
            
            if not usages:
                return {}
            
            heatmap_data = self._generate_usage_heatmap_data(usages, time_granularity)
            
            return {
                'time_granularity': time_granularity,
                'heatmap_data': heatmap_data,
                'peak_usage_periods': self._identify_peak_usage_periods(heatmap_data),
                'usage_patterns': self._analyze_temporal_usage_patterns(usages),
                'seasonal_trends': self._identify_seasonal_trends(usages),
                'recommendations': self._generate_timing_recommendations(heatmap_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating usage heatmap: {e}")
            return {}
    
    async def get_learning_path_analytics(
        self,
        learning_path_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze learning path effectiveness"""
        try:
            query = select(MaterialUsage)
            
            if learning_path_id:
                # In a real implementation, you'd filter by learning path
                # For now, we'll analyze sequential usage patterns
                pass
            
            result = await self.db.execute(query)
            usages = result.scalars().all()
            
            if not usages:
                return {}
            
            # Group by user and analyze sequences
            user_sequences = self._build_user_learning_sequences(usages)
            
            analytics = {
                'path_completion_rates': self._analyze_path_completion(user_sequences),
                'dropout_points': self._identify_dropout_points(user_sequences),
                'optimal_sequences': self._find_optimal_sequences(user_sequences),
                'prerequisite_effectiveness': self._analyze_prerequisite_effectiveness(usages),
                'skill_progression': self._track_skill_progression(user_sequences),
                'path_optimization': self._suggest_path_optimizations(user_sequences),
                'learner_journey': self._map_learner_journey(user_sequences)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error analyzing learning paths: {e}")
            return {}
    
    async def get_content_quality_metrics(self) -> Dict[str, Any]:
        """Analyze content quality and effectiveness"""
        try:
            query = select(MaterialUsage)
            result = await self.db.execute(query)
            usages = result.scalars().all()
            
            if not usages:
                return {}
            
            quality_metrics = {
                'overall_quality_score': self._calculate_overall_quality_score(usages),
                'content_ratings_distribution': self._analyze_ratings_distribution(usages),
                'engagement_quality_correlation': self._correlate_engagement_quality(usages),
                'technical_quality_indicators': self._assess_technical_quality(usages),
                'pedagogical_effectiveness': self._assess_pedagogical_effectiveness(usages),
                'accessibility_metrics': self._analyze_accessibility(usages),
                'content_freshness': self._analyze_content_freshness(usages),
                'improvement_priorities': self._identify_improvement_priorities(usages)
            }
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error analyzing content quality: {e}")
            return {}
    
    async def get_personalization_analytics(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze personalization effectiveness"""
        try:
            query = select(MaterialUsage)
            
            if user_id:
                query = query.where(MaterialUsage.user_id == user_id)
            
            result = await self.db.execute(query)
            usages = result.scalars().all()
            
            if not usages:
                return {}
            
            personalization = {
                'adaptation_effectiveness': self._measure_adaptation_effectiveness(usages),
                'recommendation_success': self._analyze_recommendation_success(usages),
                'learning_style_alignment': self._assess_learning_style_alignment(usages),
                'difficulty_adaptation': self._analyze_difficulty_adaptation(usages),
                'content_preference_patterns': self._identify_content_preferences(usages),
                'personalization_impact': self._measure_personalization_impact(usages),
                'optimization_opportunities': self._identify_optimization_opportunities(usages)
            }
            
            return personalization
            
        except Exception as e:
            logger.error(f"Error analyzing personalization: {e}")
            return {}
    
    # Helper methods
    def _empty_material_performance(self) -> Dict[str, Any]:
        """Return empty material performance structure"""
        return {
            'message': 'No material usage data available',
            'total_materials': 0,
            'total_usages': 0
        }
    
    def _calculate_material_overview(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Calculate basic material overview statistics"""
        unique_materials = len(set(u.material_id for u in usages))
        unique_users = len(set(u.user_id for u in usages))
        total_view_time = sum(u.view_duration or 0 for u in usages)
        
        return {
            'unique_materials': unique_materials,
            'unique_users': unique_users,
            'total_usages': len(usages),
            'total_view_time_minutes': total_view_time / 60 if total_view_time else 0,
            'average_usage_per_material': len(usages) / unique_materials if unique_materials else 0,
            'average_usage_per_user': len(usages) / unique_users if unique_users else 0,
            'completion_rate': len([u for u in usages if u.is_completed]) / len(usages) * 100 if usages else 0
        }
    
    def _calculate_material_engagement(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Calculate engagement metrics for materials"""
        engagement_scores = [u.calculate_engagement_score() for u in usages]
        interaction_counts = [u.interactions_count for u in usages]
        
        return {
            'average_engagement_score': np.mean(engagement_scores),
            'median_engagement_score': np.median(engagement_scores),
            'engagement_distribution': self._calculate_score_distribution(engagement_scores),
            'high_engagement_rate': len([s for s in engagement_scores if s >= 80]) / len(engagement_scores) * 100,
            'average_interactions': np.mean(interaction_counts),
            'interaction_patterns': self._analyze_interaction_patterns(usages),
            'engagement_by_material_type': self._analyze_engagement_by_type(usages)
        }
    
    def _analyze_completion_patterns(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Analyze completion patterns"""
        completion_rates = [u.completion_percentage for u in usages if u.completion_percentage is not None]
        
        if not completion_rates:
            return {'message': 'No completion data available'}
        
        return {
            'overall_completion_rate': np.mean(completion_rates),
            'median_completion_rate': np.median(completion_rates),
            'completion_distribution': self._calculate_completion_distribution(completion_rates),
            'dropout_points': self._identify_common_dropout_points(usages),
            'completion_by_type': self._analyze_completion_by_type(usages),
            'time_to_completion': self._analyze_time_to_completion(usages),
            'completion_predictors': self._identify_completion_predictors(usages)
        }
    
    def _calculate_effectiveness_scores(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Calculate material effectiveness scores"""
        effectiveness_data = []
        
        for usage in usages:
            effectiveness = usage.get_learning_effectiveness()
            effectiveness_data.append(effectiveness)
        
        if not effectiveness_data:
            return {'message': 'No effectiveness data available'}
        
        # Aggregate effectiveness scores
        overall_scores = [e.get('overall_score', 0) for e in effectiveness_data]
        
        return {
            'average_effectiveness_score': np.mean(overall_scores),
            'effectiveness_distribution': self._calculate_score_distribution(overall_scores),
            'top_performing_materials': self._identify_top_materials(usages, effectiveness_data),
            'underperforming_materials': self._identify_underperforming_materials(usages, effectiveness_data),
            'effectiveness_factors': self._analyze_effectiveness_factors(effectiveness_data),
            'improvement_correlation': self._correlate_with_improvement(usages)
        }
    
    def _analyze_user_feedback(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Analyze user feedback and ratings"""
        ratings = [u.user_rating for u in usages if u.user_rating is not None]
        difficulty_ratings = [u.difficulty_rating for u in usages if u.difficulty_rating is not None]
        usefulness_ratings = [u.usefulness_rating for u in usages if u.usefulness_rating is not None]
        
        feedback_analysis = {
            'average_rating': np.mean(ratings) if ratings else 0,
            'rating_distribution': self._calculate_rating_distribution(ratings),
            'satisfaction_rate': len([r for r in ratings if r >= 4]) / len(ratings) * 100 if ratings else 0,
            'average_difficulty_rating': np.mean(difficulty_ratings) if difficulty_ratings else 0,
            'average_usefulness_rating': np.mean(usefulness_ratings) if usefulness_ratings else 0,
            'recommendation_rate': len([u for u in usages if u.would_recommend]) / len(usages) * 100 if usages else 0,
            'feedback_trends': self._analyze_feedback_trends(usages),
            'sentiment_analysis': self._perform_sentiment_analysis(usages)
        }
        
        return feedback_analysis
    
    def _identify_usage_patterns(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Identify common usage patterns"""
        # Temporal patterns
        hour_usage = {}
        day_usage = {}
        
        for usage in usages:
            hour = usage.access_date.hour
            day = usage.access_date.strftime('%A')
            
            hour_usage[hour] = hour_usage.get(hour, 0) + 1
            day_usage[day] = day_usage.get(day, 0) + 1
        
        # Usage behaviors
        usage_patterns = {}
        for usage in usages:
            pattern = usage.get_usage_pattern()
            usage_patterns[pattern] = usage_patterns.get(pattern, 0) + 1
        
        return {
            'temporal_patterns': {
                'peak_hour': max(hour_usage, key=hour_usage.get) if hour_usage else None,
                'peak_day': max(day_usage, key=day_usage.get) if day_usage else None,
                'hourly_distribution': hour_usage,
                'daily_distribution': day_usage
            },
            'behavioral_patterns': usage_patterns,
            'device_patterns': self._analyze_device_patterns(usages),
            'access_patterns': self._analyze_access_patterns(usages),
            'session_patterns': self._analyze_session_patterns(usages)
        }
    
    async def _assess_learning_outcomes(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Assess learning outcomes from material usage"""
        # This would typically correlate with test scores, performance improvements, etc.
        # For now, use engagement and completion as proxies
        
        outcome_indicators = []
        for usage in usages:
            effectiveness = usage.get_learning_effectiveness()
            outcome_indicators.append({
                'material_id': usage.material_id,
                'user_id': usage.user_id,
                'effectiveness_score': effectiveness.get('overall_score', 0),
                'completion_rate': usage.completion_percentage or 0,
                'engagement_score': usage.calculate_engagement_score(),
                'retention_indicator': usage.revisit_count > 0
            })
        
        return {
            'average_learning_outcome': np.mean([o['effectiveness_score'] for o in outcome_indicators]),
            'knowledge_retention_rate': len([o for o in outcome_indicators if o['retention_indicator']]) / len(outcome_indicators) * 100 if outcome_indicators else 0,
            'skill_development_indicators': self._assess_skill_development(usages),
            'learning_transfer': self._assess_learning_transfer(usages),
            'outcome_predictors': self._identify_outcome_predictors(outcome_indicators)
        }
    
    def _generate_content_recommendations(self, usages: List[MaterialUsage]) -> List[str]:
        """Generate content improvement recommendations"""
        recommendations = []
        
        # Analyze common issues
        low_completion_materials = [u for u in usages if u.completion_percentage and u.completion_percentage < 50]
        high_difficulty_ratings = [u for u in usages if u.difficulty_rating and u.difficulty_rating >= 4]
        low_engagement_materials = [u for u in usages if u.calculate_engagement_score() < 50]
        
        if low_completion_materials:
            recommendations.append("Review materials with low completion rates - consider breaking into smaller segments")
        
        if high_difficulty_ratings:
            recommendations.append("Provide additional scaffolding for materials rated as too difficult")
        
        if low_engagement_materials:
            recommendations.append("Add interactive elements to increase engagement")
        
        # Technical issues
        technical_issues = [u for u in usages if u.technical_issues and len(u.technical_issues) > 0]
        if technical_issues:
            recommendations.append("Address technical issues reported by users")
        
        # Loading time issues
        slow_loading = [u for u in usages if u.loading_time and u.loading_time > 10]
        if slow_loading:
            recommendations.append("Optimize loading times for better user experience")
        
        return recommendations[:5]
    
    async def _compare_material_performance(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Compare performance across materials"""
        material_performance = {}
        
        for usage in usages:
            material_id = usage.material_id
            if material_id not in material_performance:
                material_performance[material_id] = {
                    'usages': [],
                    'total_users': set(),
                    'engagement_scores': [],
                    'completion_rates': [],
                    'ratings': []
                }
            
            material_performance[material_id]['usages'].append(usage)
            material_performance[material_id]['total_users'].add(usage.user_id)
            material_performance[material_id]['engagement_scores'].append(usage.calculate_engagement_score())
            
            if usage.completion_percentage:
                material_performance[material_id]['completion_rates'].append(usage.completion_percentage)
            
            if usage.user_rating:
                material_performance[material_id]['ratings'].append(usage.user_rating)
        
        # Calculate averages and rank materials
        material_rankings = []
        for material_id, data in material_performance.items():
            avg_engagement = np.mean(data['engagement_scores'])
            avg_completion = np.mean(data['completion_rates']) if data['completion_rates'] else 0
            avg_rating = np.mean(data['ratings']) if data['ratings'] else 0
            
            overall_score = (avg_engagement * 0.4 + avg_completion * 0.4 + avg_rating * 20 * 0.2)
            
            material_rankings.append({
                'material_id': material_id,
                'overall_score': overall_score,
                'avg_engagement': avg_engagement,
                'avg_completion': avg_completion,
                'avg_rating': avg_rating,
                'unique_users': len(data['total_users']),
                'total_usages': len(data['usages'])
            })
        
        # Sort by overall score
        material_rankings.sort(key=lambda x: x['overall_score'], reverse=True)
        
        return {
            'top_performing_materials': material_rankings[:10],
            'bottom_performing_materials': material_rankings[-10:],
            'performance_distribution': self._analyze_performance_distribution(material_rankings),
            'benchmarks': self._calculate_performance_benchmarks(material_rankings)
        }
    
    def _analyze_content_overview(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Analyze content overview statistics"""
        # Group by content attributes
        by_type = {}
        by_subject = {}
        by_difficulty = {}
        
        for usage in usages:
            # By type
            type_key = usage.material_type or 'unknown'
            if type_key not in by_type:
                by_type[type_key] = {'count': 0, 'engagement': []}
            by_type[type_key]['count'] += 1
            by_type[type_key]['engagement'].append(usage.calculate_engagement_score())
            
            # By subject
            subject_key = usage.subject or 'unknown'
            if subject_key not in by_subject:
                by_subject[subject_key] = {'count': 0, 'engagement': []}
            by_subject[subject_key]['count'] += 1
            by_subject[subject_key]['engagement'].append(usage.calculate_engagement_score())
            
            # By difficulty
            difficulty_key = usage.difficulty_level or 'unknown'
            if difficulty_key not in by_difficulty:
                by_difficulty[difficulty_key] = {'count': 0, 'engagement': []}
            by_difficulty[difficulty_key]['count'] += 1
            by_difficulty[difficulty_key]['engagement'].append(usage.calculate_engagement_score())
        
        # Calculate averages
        for category in [by_type, by_subject, by_difficulty]:
            for key, data in category.items():
                data['avg_engagement'] = np.mean(data['engagement'])
        
        return {
            'content_by_type': by_type,
            'content_by_subject': by_subject,
            'content_by_difficulty': by_difficulty,
            'total_content_pieces': len(set(u.material_id for u in usages)),
            'content_diversity_index': self._calculate_diversity_index(usages)
        }
    
    def _rank_content_popularity(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Rank content by popularity metrics"""
        material_stats = {}
        
        for usage in usages:
            material_id = usage.material_id
            if material_id not in material_stats:
                material_stats[material_id] = {
                    'access_count': 0,
                    'unique_users': set(),
                    'total_view_time': 0,
                    'bookmarks': 0,
                    'ratings': []
                }
            
            material_stats[material_id]['access_count'] += 1
            material_stats[material_id]['unique_users'].add(usage.user_id)
            material_stats[material_id]['total_view_time'] += usage.view_duration or 0
            
            if usage.bookmark_added:
                material_stats[material_id]['bookmarks'] += 1
            
            if usage.user_rating:
                material_stats[material_id]['ratings'].append(usage.user_rating)
        
        # Calculate popularity scores
        popularity_rankings = []
        for material_id, stats in material_stats.items():
            popularity_score = (
                stats['access_count'] * 0.3 +
                len(stats['unique_users']) * 0.4 +
                stats['bookmarks'] * 0.2 +
                (np.mean(stats['ratings']) if stats['ratings'] else 0) * 10 * 0.1
            )
            
            popularity_rankings.append({
                'material_id': material_id,
                'popularity_score': popularity_score,
                'access_count': stats['access_count'],
                'unique_users': len(stats['unique_users']),
                'avg_rating': np.mean(stats['ratings']) if stats['ratings'] else 0,
                'total_view_time': stats['total_view_time']
            })
        
        popularity_rankings.sort(key=lambda x: x['popularity_score'], reverse=True)
        
        return {
            'most_popular': popularity_rankings[:10],
            'least_popular': popularity_rankings[-10:],
            'popularity_distribution': self._analyze_popularity_distribution(popularity_rankings)
        }
    
    def _analyze_engagement_by_type(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Analyze engagement by material type"""
        type_engagement = {}
        
        for usage in usages:
            material_type = usage.material_type or 'unknown'
            if material_type not in type_engagement:
                type_engagement[material_type] = []
            
            type_engagement[material_type].append(usage.calculate_engagement_score())
        
        # Calculate averages and statistics
        type_stats = {}
        for material_type, scores in type_engagement.items():
            type_stats[material_type] = {
                'avg_engagement': np.mean(scores),
                'median_engagement': np.median(scores),
                'count': len(scores),
                'high_engagement_rate': len([s for s in scores if s >= 80]) / len(scores) * 100
            }
        
        return type_stats
    
    def _generate_usage_heatmap_data(self, usages: List[MaterialUsage], granularity: str) -> Dict[str, Any]:
        """Generate heatmap data for usage patterns"""
        heatmap = {}
        
        for usage in usages:
            # Determine time key based on granularity
            if granularity == 'hour':
                time_key = usage.access_date.hour
            elif granularity == 'day':
                time_key = usage.access_date.strftime('%A')
            elif granularity == 'week':
                time_key = f"Week {usage.access_date.isocalendar()[1]}"
            else:  # month
                time_key = usage.access_date.strftime('%B')
            
            if time_key not in heatmap:
                heatmap[time_key] = 0
            heatmap[time_key] += 1
        
        return heatmap
    
    def _identify_peak_usage_periods(self, heatmap_data: Dict[str, Any]) -> Dict[str, Any]:
        """Identify peak usage periods"""
        if not heatmap_data:
            return {}
        
        peak_period = max(heatmap_data, key=heatmap_data.get)
        peak_count = heatmap_data[peak_period]
        
        return {
            'peak_period': peak_period,
            'peak_usage_count': peak_count,
            'peak_percentage': (peak_count / sum(heatmap_data.values())) * 100
        }
    
    def _build_user_learning_sequences(self, usages: List[MaterialUsage]) -> Dict[str, List[MaterialUsage]]:
        """Build learning sequences for each user"""
        user_sequences = {}
        
        for usage in usages:
            user_id = usage.user_id
            if user_id not in user_sequences:
                user_sequences[user_id] = []
            user_sequences[user_id].append(usage)
        
        # Sort sequences by access date
        for user_id in user_sequences:
            user_sequences[user_id].sort(key=lambda x: x.access_date)
        
        return user_sequences
    
    def _analyze_path_completion(self, user_sequences: Dict[str, List[MaterialUsage]]) -> Dict[str, Any]:
        """Analyze learning path completion rates"""
        completion_data = []
        
        for user_id, sequence in user_sequences.items():
            completed_materials = len([u for u in sequence if u.is_completed])
            total_materials = len(sequence)
            completion_rate = (completed_materials / total_materials) * 100 if total_materials > 0 else 0
            
            completion_data.append({
                'user_id': user_id,
                'completion_rate': completion_rate,
                'completed_materials': completed_materials,
                'total_materials': total_materials
            })
        
        return {
            'average_completion_rate': np.mean([c['completion_rate'] for c in completion_data]),
            'completion_distribution': self._calculate_completion_distribution([c['completion_rate'] for c in completion_data]),
            'fully_completed_paths': len([c for c in completion_data if c['completion_rate'] == 100]),
            'abandoned_paths': len([c for c in completion_data if c['completion_rate'] < 10])
        }
    
    def _identify_dropout_points(self, user_sequences: Dict[str, List[MaterialUsage]]) -> Dict[str, Any]:
        """Identify common dropout points in learning paths"""
        position_dropouts = {}
        
        for user_id, sequence in user_sequences.items():
            # Find the last completed material
            last_completed_index = -1
            for i, usage in enumerate(sequence):
                if usage.is_completed:
                    last_completed_index = i
            
            # If user didn't complete everything, mark dropout point
            if last_completed_index < len(sequence) - 1:
                dropout_position = last_completed_index + 1
                if dropout_position not in position_dropouts:
                    position_dropouts[dropout_position] = 0
                position_dropouts[dropout_position] += 1
        
        return {
            'dropout_by_position': position_dropouts,
            'most_common_dropout_point': max(position_dropouts, key=position_dropouts.get) if position_dropouts else None,
            'early_dropout_rate': sum(position_dropouts.get(i, 0) for i in range(3)) / len(user_sequences) * 100 if user_sequences else 0
        }
    
    # Additional helper methods for various calculations...
    
    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of scores"""
        if not scores:
            return {}
        
        distribution = {
            '0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0
        }
        
        for score in scores:
            if score <= 20:
                distribution['0-20'] += 1
            elif score <= 40:
                distribution['21-40'] += 1
            elif score <= 60:
                distribution['41-60'] += 1
            elif score <= 80:
                distribution['61-80'] += 1
            else:
                distribution['81-100'] += 1
        
        return distribution
    
    def _identify_top_materials(self, usages: List[MaterialUsage], effectiveness_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify top performing materials"""
        material_effectiveness = {}
        
        for i, usage in enumerate(usages):
            if i < len(effectiveness_data):
                material_id = usage.material_id
                effectiveness_score = effectiveness_data[i].get('overall_score', 0)
                
                if material_id not in material_effectiveness:
                    material_effectiveness[material_id] = []
                material_effectiveness[material_id].append(effectiveness_score)
        
        # Calculate average effectiveness per material
        material_averages = []
        for material_id, scores in material_effectiveness.items():
            avg_score = np.mean(scores)
            material_averages.append({
                'material_id': material_id,
                'avg_effectiveness': avg_score,
                'usage_count': len(scores)
            })
        
        # Sort by effectiveness and return top 10
        material_averages.sort(key=lambda x: x['avg_effectiveness'], reverse=True)
        return material_averages[:10]
    
    def _correlate_engagement_quality(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Correlate engagement with quality ratings"""
        engagement_quality_pairs = []
        
        for usage in usages:
            if usage.user_rating:
                engagement_score = usage.calculate_engagement_score()
                quality_rating = usage.user_rating
                engagement_quality_pairs.append((engagement_score, quality_rating))
        
        if len(engagement_quality_pairs) > 1:
            engagements, ratings = zip(*engagement_quality_pairs)
            correlation = np.corrcoef(engagements, ratings)[0, 1]
            
            return {
                'correlation_coefficient': correlation if not np.isnan(correlation) else 0,
                'correlation_strength': 'strong' if abs(correlation) > 0.7 else 'moderate' if abs(correlation) > 0.4 else 'weak',
                'data_points': len(engagement_quality_pairs)
            }
        
        return {'correlation_coefficient': 0, 'data_points': len(engagement_quality_pairs)}
    
    def _assess_technical_quality(self, usages: List[MaterialUsage]) -> Dict[str, Any]:
        """Assess technical quality indicators"""
        loading_times = [u.loading_time for u in usages if u.loading_time is not None]
        error_counts = [u.error_count for u in usages]
        technical_issues = [u for u in usages if u.technical_issues and len(u.technical_issues) > 0]
        
        return {
            'average_loading_time': np.mean(loading_times) if loading_times else 0,
            'error_rate': sum(error_counts) / len(usages) if usages else 0,
            'technical_issue_rate': len(technical_issues) / len(usages) * 100 if usages else 0,
            'performance_score': self._calculate_technical_performance_score(loading_times, error_counts)
        }
    
    def _calculate_technical_performance_score(self, loading_times: List[float], error_counts: List[int]) -> float:
        """Calculate technical performance score"""
        if not loading_times and not error_counts:
            return 0
        
        score = 100
        
        # Penalize slow loading times
        if loading_times:
            avg_loading_time = np.mean(loading_times)
            if avg_loading_time > 3:  # More than 3 seconds
                score -= min((avg_loading_time - 3) * 10, 30)
        
        # Penalize errors
        if error_counts:
            avg_errors = np.mean(error_counts)
            score -= min(avg_errors * 5, 40)
        
        return max(score, 0)