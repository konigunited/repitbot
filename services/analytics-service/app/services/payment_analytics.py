from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
import pandas as pd
import numpy as np
from ..models.payment_summary import PaymentSummary
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)


class PaymentAnalyticsService:
    """Service for payment analytics and financial metrics"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
    async def get_financial_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        tutor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive financial summary"""
        try:
            query = select(PaymentSummary)
            
            filters = []
            if start_date:
                filters.append(PaymentSummary.payment_date >= start_date)
            if end_date:
                filters.append(PaymentSummary.payment_date <= end_date)
            if user_id:
                filters.append(PaymentSummary.user_id == user_id)
            if tutor_id:
                filters.append(PaymentSummary.tutor_id == tutor_id)
                
            if filters:
                query = query.where(and_(*filters))
                
            result = await self.db.execute(query)
            payments = result.scalars().all()
            
            if not payments:
                return self._empty_financial_summary()
            
            summary = {
                'total_revenue': sum(p.amount for p in payments),
                'total_transactions': len(payments),
                'completed_payments': len([p for p in payments if p.status == 'completed']),
                'failed_payments': len([p for p in payments if p.status == 'failed']),
                'refunded_amount': sum(p.refund_amount for p in payments),
                'net_revenue': sum(p.get_net_amount() for p in payments),
                'average_transaction_value': np.mean([p.amount for p in payments]),
                'success_rate': len([p for p in payments if p.status == 'completed']) / len(payments) * 100,
                'payment_methods': self._analyze_payment_methods(payments),
                'currency_breakdown': self._analyze_currencies(payments),
                'monthly_revenue_trend': await self._calculate_revenue_trend(payments),
                'customer_segments': self._analyze_customer_segments(payments),
                'churn_indicators': self._calculate_churn_indicators(payments),
                'profit_margins': self._calculate_profit_margins(payments)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting financial summary: {e}")
            return self._empty_financial_summary()
    
    async def get_revenue_analytics(
        self,
        period: str = 'month',
        breakdown_by: str = 'time',  # time, payment_method, service_type, geography
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get detailed revenue analytics"""
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=365)
            
            query = select(PaymentSummary).where(
                and_(
                    PaymentSummary.payment_date >= start_date,
                    PaymentSummary.payment_date <= end_date,
                    PaymentSummary.status == 'completed'
                )
            ).order_by(asc(PaymentSummary.payment_date))
            
            result = await self.db.execute(query)
            payments = result.scalars().all()
            
            if not payments:
                return {}
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame([{
                'date': p.payment_date,
                'amount': p.amount,
                'payment_method': p.payment_method,
                'payment_type': p.payment_type,
                'country': p.country,
                'user_id': p.user_id,
                'tutor_id': p.tutor_id,
                'is_recurring': p.is_recurring,
                'discount_amount': p.discount_amount
            } for p in payments])
            
            analytics = {
                'period': period,
                'breakdown_type': breakdown_by,
                'total_revenue': df['amount'].sum(),
                'total_transactions': len(df),
                'period_analysis': self._analyze_by_period(df, period),
                'growth_metrics': self._calculate_growth_metrics(df, period),
                'seasonal_patterns': self._identify_seasonal_patterns(df)
            }
            
            # Add specific breakdown analysis
            if breakdown_by == 'payment_method':
                analytics['payment_method_breakdown'] = self._breakdown_by_payment_method(df)
            elif breakdown_by == 'service_type':
                analytics['service_type_breakdown'] = self._breakdown_by_service_type(df)
            elif breakdown_by == 'geography':
                analytics['geography_breakdown'] = self._breakdown_by_geography(df)
            else:
                analytics['time_breakdown'] = self._breakdown_by_time(df, period)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}")
            return {}
    
    async def get_customer_lifetime_value(
        self,
        user_id: Optional[str] = None,
        segment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate customer lifetime value metrics"""
        try:
            query = select(PaymentSummary).where(PaymentSummary.status == 'completed')
            
            if user_id:
                query = query.where(PaymentSummary.user_id == user_id)
            
            result = await self.db.execute(query)
            payments = result.scalars().all()
            
            if not payments:
                return {}
            
            # Group by customer
            customer_data = {}
            for payment in payments:
                if payment.user_id not in customer_data:
                    customer_data[payment.user_id] = {
                        'total_spent': 0,
                        'transaction_count': 0,
                        'first_payment': payment.payment_date,
                        'last_payment': payment.payment_date,
                        'payments': []
                    }
                
                customer_data[payment.user_id]['total_spent'] += payment.amount
                customer_data[payment.user_id]['transaction_count'] += 1
                customer_data[payment.user_id]['payments'].append(payment)
                
                if payment.payment_date < customer_data[payment.user_id]['first_payment']:
                    customer_data[payment.user_id]['first_payment'] = payment.payment_date
                if payment.payment_date > customer_data[payment.user_id]['last_payment']:
                    customer_data[payment.user_id]['last_payment'] = payment.payment_date
            
            # Calculate CLV metrics
            clv_metrics = []
            for user_id, data in customer_data.items():
                customer_lifetime_days = (data['last_payment'] - data['first_payment']).days + 1
                avg_transaction_value = data['total_spent'] / data['transaction_count']
                transaction_frequency = data['transaction_count'] / (customer_lifetime_days / 30)  # per month
                
                clv_metrics.append({
                    'user_id': user_id,
                    'total_spent': data['total_spent'],
                    'transaction_count': data['transaction_count'],
                    'avg_transaction_value': avg_transaction_value,
                    'customer_lifetime_days': customer_lifetime_days,
                    'transaction_frequency_monthly': transaction_frequency,
                    'predicted_clv': avg_transaction_value * transaction_frequency * 24  # 2 years
                })
            
            # Aggregate statistics
            total_customers = len(clv_metrics)
            avg_clv = np.mean([m['predicted_clv'] for m in clv_metrics])
            median_clv = np.median([m['predicted_clv'] for m in clv_metrics])
            
            return {
                'total_customers': total_customers,
                'average_clv': avg_clv,
                'median_clv': median_clv,
                'customer_segments': self._segment_customers_by_clv(clv_metrics),
                'top_customers': sorted(clv_metrics, key=lambda x: x['predicted_clv'], reverse=True)[:10],
                'clv_distribution': self._calculate_clv_distribution(clv_metrics),
                'retention_impact': await self._calculate_retention_impact(customer_data)
            }
            
        except Exception as e:
            logger.error(f"Error calculating CLV: {e}")
            return {}
    
    async def get_payment_patterns(
        self,
        analysis_type: str = 'temporal'  # temporal, behavioral, risk, conversion
    ) -> Dict[str, Any]:
        """Analyze payment patterns and behaviors"""
        try:
            query = select(PaymentSummary)
            result = await self.db.execute(query)
            payments = result.scalars().all()
            
            if not payments:
                return {}
            
            if analysis_type == 'temporal':
                return await self._analyze_temporal_patterns(payments)
            elif analysis_type == 'behavioral':
                return await self._analyze_behavioral_patterns(payments)
            elif analysis_type == 'risk':
                return await self._analyze_risk_patterns(payments)
            elif analysis_type == 'conversion':
                return await self._analyze_conversion_patterns(payments)
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error analyzing payment patterns: {e}")
            return {}
    
    async def get_subscription_analytics(self) -> Dict[str, Any]:
        """Analyze subscription-based payments and recurring revenue"""
        try:
            query = select(PaymentSummary).where(PaymentSummary.is_recurring == True)
            result = await self.db.execute(query)
            subscriptions = result.scalars().all()
            
            if not subscriptions:
                return {'message': 'No subscription data available'}
            
            # Group by subscription_id
            subscription_groups = {}
            for sub in subscriptions:
                if sub.subscription_id:
                    if sub.subscription_id not in subscription_groups:
                        subscription_groups[sub.subscription_id] = []
                    subscription_groups[sub.subscription_id].append(sub)
            
            # Calculate MRR (Monthly Recurring Revenue)
            current_date = datetime.utcnow()
            active_subscriptions = []
            
            for sub_id, payments in subscription_groups.items():
                latest_payment = max(payments, key=lambda x: x.payment_date)
                if latest_payment.next_payment_date and latest_payment.next_payment_date > current_date:
                    active_subscriptions.append({
                        'subscription_id': sub_id,
                        'monthly_value': latest_payment.amount,  # Assuming monthly billing
                        'user_id': latest_payment.user_id,
                        'billing_cycle': latest_payment.billing_cycle,
                        'start_date': min(payments, key=lambda x: x.payment_date).payment_date,
                        'payment_count': len(payments)
                    })
            
            mrr = sum(sub['monthly_value'] for sub in active_subscriptions)
            
            analytics = {
                'total_subscriptions': len(subscription_groups),
                'active_subscriptions': len(active_subscriptions),
                'monthly_recurring_revenue': mrr,
                'annual_recurring_revenue': mrr * 12,
                'average_subscription_value': mrr / len(active_subscriptions) if active_subscriptions else 0,
                'subscription_retention_rate': self._calculate_subscription_retention(subscription_groups),
                'churn_rate': self._calculate_subscription_churn(subscription_groups),
                'upgrade_downgrade_analysis': self._analyze_subscription_changes(subscription_groups),
                'billing_cycle_distribution': self._analyze_billing_cycles(subscriptions)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting subscription analytics: {e}")
            return {}
    
    async def get_payment_failure_analysis(self) -> Dict[str, Any]:
        """Analyze payment failures and recovery opportunities"""
        try:
            query = select(PaymentSummary)
            result = await self.db.execute(query)
            payments = result.scalars().all()
            
            failed_payments = [p for p in payments if p.status == 'failed']
            total_payments = len(payments)
            
            if not failed_payments:
                return {'message': 'No payment failures to analyze'}
            
            analysis = {
                'total_failed_payments': len(failed_payments),
                'failure_rate': (len(failed_payments) / total_payments) * 100 if total_payments > 0 else 0,
                'lost_revenue': sum(p.amount for p in failed_payments),
                'failure_reasons': self._analyze_failure_reasons(failed_payments),
                'failure_by_payment_method': self._analyze_failures_by_method(failed_payments),
                'failure_patterns': self._analyze_failure_patterns(failed_payments),
                'recovery_opportunities': self._identify_recovery_opportunities(failed_payments),
                'prevention_recommendations': self._generate_failure_prevention_recommendations(failed_payments)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing payment failures: {e}")
            return {}
    
    # Helper methods
    def _empty_financial_summary(self) -> Dict[str, Any]:
        """Return empty financial summary structure"""
        return {
            'total_revenue': 0,
            'total_transactions': 0,
            'completed_payments': 0,
            'failed_payments': 0,
            'net_revenue': 0,
            'average_transaction_value': 0,
            'success_rate': 0
        }
    
    def _analyze_payment_methods(self, payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Analyze payment method distribution and performance"""
        method_stats = {}
        
        for payment in payments:
            method = payment.payment_method
            if method not in method_stats:
                method_stats[method] = {
                    'count': 0,
                    'total_amount': 0,
                    'successful': 0,
                    'failed': 0
                }
            
            method_stats[method]['count'] += 1
            method_stats[method]['total_amount'] += payment.amount
            
            if payment.status == 'completed':
                method_stats[method]['successful'] += 1
            elif payment.status == 'failed':
                method_stats[method]['failed'] += 1
        
        # Calculate success rates and averages
        for method, stats in method_stats.items():
            stats['success_rate'] = (stats['successful'] / stats['count']) * 100
            stats['average_amount'] = stats['total_amount'] / stats['count']
        
        return method_stats
    
    def _analyze_currencies(self, payments: List[PaymentSummary]) -> Dict[str, Dict[str, Any]]:
        """Analyze currency distribution"""
        currency_stats = {}
        
        for payment in payments:
            currency = payment.currency
            if currency not in currency_stats:
                currency_stats[currency] = {'count': 0, 'total_amount': 0}
            
            currency_stats[currency]['count'] += 1
            currency_stats[currency]['total_amount'] += payment.amount
        
        return currency_stats
    
    async def _calculate_revenue_trend(self, payments: List[PaymentSummary]) -> List[Dict[str, Any]]:
        """Calculate monthly revenue trend"""
        monthly_revenue = {}
        
        for payment in payments:
            if payment.status == 'completed':
                month_key = payment.payment_date.strftime('%Y-%m')
                if month_key not in monthly_revenue:
                    monthly_revenue[month_key] = 0
                monthly_revenue[month_key] += payment.amount
        
        trend = []
        for month, revenue in sorted(monthly_revenue.items()):
            trend.append({'month': month, 'revenue': revenue})
        
        return trend
    
    def _analyze_customer_segments(self, payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Segment customers based on payment behavior"""
        customer_spending = {}
        
        for payment in payments:
            if payment.status == 'completed':
                user_id = payment.user_id
                if user_id not in customer_spending:
                    customer_spending[user_id] = 0
                customer_spending[user_id] += payment.amount
        
        if not customer_spending:
            return {}
        
        spending_values = list(customer_spending.values())
        q1 = np.percentile(spending_values, 25)
        q3 = np.percentile(spending_values, 75)
        
        segments = {
            'high_value': len([s for s in spending_values if s >= q3]),
            'medium_value': len([s for s in spending_values if q1 <= s < q3]),
            'low_value': len([s for s in spending_values if s < q1]),
            'total_customers': len(spending_values),
            'average_customer_value': np.mean(spending_values),
            'median_customer_value': np.median(spending_values)
        }
        
        return segments
    
    def _calculate_churn_indicators(self, payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Calculate churn risk indicators"""
        current_date = datetime.utcnow()
        customer_last_payment = {}
        
        for payment in payments:
            if payment.status == 'completed':
                user_id = payment.user_id
                if user_id not in customer_last_payment or payment.payment_date > customer_last_payment[user_id]:
                    customer_last_payment[user_id] = payment.payment_date
        
        churn_risk = {
            'at_risk_30_days': 0,
            'at_risk_60_days': 0,
            'at_risk_90_days': 0,
            'total_customers': len(customer_last_payment)
        }
        
        for user_id, last_payment_date in customer_last_payment.items():
            days_since_payment = (current_date - last_payment_date).days
            
            if days_since_payment >= 90:
                churn_risk['at_risk_90_days'] += 1
            elif days_since_payment >= 60:
                churn_risk['at_risk_60_days'] += 1
            elif days_since_payment >= 30:
                churn_risk['at_risk_30_days'] += 1
        
        return churn_risk
    
    def _calculate_profit_margins(self, payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Calculate profit margins"""
        total_revenue = sum(p.amount for p in payments if p.status == 'completed')
        total_costs = sum(
            p.fee_amount + p.tutor_commission + p.affiliate_commission + p.platform_fee
            for p in payments if p.status == 'completed'
        )
        
        gross_profit = total_revenue - total_costs
        margin_percentage = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            'total_revenue': total_revenue,
            'total_costs': total_costs,
            'gross_profit': gross_profit,
            'margin_percentage': margin_percentage,
            'average_transaction_margin': margin_percentage  # Simplified
        }
    
    def _analyze_by_period(self, df: pd.DataFrame, period: str) -> Dict[str, Any]:
        """Analyze revenue by time period"""
        df['period'] = self._group_by_period(df['date'], period)
        
        period_analysis = df.groupby('period').agg({
            'amount': ['sum', 'count', 'mean'],
            'user_id': 'nunique'
        }).round(2)
        
        return period_analysis.to_dict()
    
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
    
    def _calculate_growth_metrics(self, df: pd.DataFrame, period: str) -> Dict[str, Any]:
        """Calculate growth metrics"""
        df['period'] = self._group_by_period(df['date'], period)
        revenue_by_period = df.groupby('period')['amount'].sum().sort_index()
        
        if len(revenue_by_period) < 2:
            return {'growth_rate': 0, 'periods_analyzed': len(revenue_by_period)}
        
        # Calculate period-over-period growth
        growth_rates = []
        for i in range(1, len(revenue_by_period)):
            prev_revenue = revenue_by_period.iloc[i-1]
            curr_revenue = revenue_by_period.iloc[i]
            
            if prev_revenue > 0:
                growth_rate = ((curr_revenue - prev_revenue) / prev_revenue) * 100
                growth_rates.append(growth_rate)
        
        return {
            'average_growth_rate': np.mean(growth_rates) if growth_rates else 0,
            'compound_growth_rate': self._calculate_compound_growth_rate(revenue_by_period),
            'growth_trend': 'increasing' if np.mean(growth_rates) > 0 else 'decreasing',
            'periods_analyzed': len(revenue_by_period)
        }
    
    def _calculate_compound_growth_rate(self, revenue_series: pd.Series) -> float:
        """Calculate compound annual growth rate"""
        if len(revenue_series) < 2:
            return 0
        
        first_value = revenue_series.iloc[0]
        last_value = revenue_series.iloc[-1]
        periods = len(revenue_series) - 1
        
        if first_value <= 0:
            return 0
        
        cagr = ((last_value / first_value) ** (1/periods) - 1) * 100
        return cagr
    
    def _identify_seasonal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify seasonal revenue patterns"""
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['day_of_week'] = df['date'].dt.day_of_week
        
        monthly_avg = df.groupby('month')['amount'].mean().to_dict()
        quarterly_avg = df.groupby('quarter')['amount'].mean().to_dict()
        weekly_avg = df.groupby('day_of_week')['amount'].mean().to_dict()
        
        return {
            'monthly_patterns': monthly_avg,
            'quarterly_patterns': quarterly_avg,
            'weekly_patterns': weekly_avg,
            'peak_month': max(monthly_avg, key=monthly_avg.get),
            'peak_quarter': max(quarterly_avg, key=quarterly_avg.get),
            'peak_day': max(weekly_avg, key=weekly_avg.get)
        }
    
    def _breakdown_by_payment_method(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Break down revenue by payment method"""
        method_analysis = df.groupby('payment_method').agg({
            'amount': ['sum', 'count', 'mean'],
            'user_id': 'nunique'
        }).round(2)
        
        return method_analysis.to_dict()
    
    def _breakdown_by_service_type(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Break down revenue by service type"""
        service_analysis = df.groupby('payment_type').agg({
            'amount': ['sum', 'count', 'mean'],
            'user_id': 'nunique'
        }).round(2)
        
        return service_analysis.to_dict()
    
    def _breakdown_by_geography(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Break down revenue by geography"""
        geo_analysis = df.groupby('country').agg({
            'amount': ['sum', 'count', 'mean'],
            'user_id': 'nunique'
        }).round(2)
        
        return geo_analysis.to_dict()
    
    def _breakdown_by_time(self, df: pd.DataFrame, period: str) -> Dict[str, Any]:
        """Break down revenue by time periods"""
        df['period'] = self._group_by_period(df['date'], period)
        
        time_analysis = df.groupby('period').agg({
            'amount': ['sum', 'count', 'mean'],
            'user_id': 'nunique'
        }).round(2)
        
        return time_analysis.to_dict()
    
    def _segment_customers_by_clv(self, clv_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Segment customers by CLV"""
        clv_values = [m['predicted_clv'] for m in clv_metrics]
        
        if not clv_values:
            return {}
        
        q1 = np.percentile(clv_values, 25)
        q2 = np.percentile(clv_values, 50)
        q3 = np.percentile(clv_values, 75)
        
        segments = {
            'champions': [m for m in clv_metrics if m['predicted_clv'] >= q3],
            'loyal_customers': [m for m in clv_metrics if q2 <= m['predicted_clv'] < q3],
            'potential_loyalists': [m for m in clv_metrics if q1 <= m['predicted_clv'] < q2],
            'at_risk': [m for m in clv_metrics if m['predicted_clv'] < q1]
        }
        
        return {
            'champions': len(segments['champions']),
            'loyal_customers': len(segments['loyal_customers']),
            'potential_loyalists': len(segments['potential_loyalists']),
            'at_risk': len(segments['at_risk']),
            'segment_thresholds': {'q1': q1, 'q2': q2, 'q3': q3}
        }
    
    def _calculate_clv_distribution(self, clv_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate CLV distribution statistics"""
        clv_values = [m['predicted_clv'] for m in clv_metrics]
        
        if not clv_values:
            return {}
        
        return {
            'min': min(clv_values),
            'max': max(clv_values),
            'mean': np.mean(clv_values),
            'median': np.median(clv_values),
            'std_dev': np.std(clv_values),
            'percentile_90': np.percentile(clv_values, 90),
            'percentile_95': np.percentile(clv_values, 95)
        }
    
    async def _calculate_retention_impact(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate retention impact on CLV"""
        # This would typically involve more complex analysis
        # For now, return basic retention metrics
        return {
            'retention_rate_impact': 'placeholder',
            'retention_analysis': 'would_require_historical_data'
        }
    
    async def _analyze_temporal_patterns(self, payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Analyze temporal payment patterns"""
        # Hour of day analysis
        hour_distribution = {}
        day_distribution = {}
        
        for payment in payments:
            hour = payment.payment_date.hour
            day = payment.payment_date.strftime('%A')
            
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
            day_distribution[day] = day_distribution.get(day, 0) + 1
        
        return {
            'peak_payment_hour': max(hour_distribution, key=hour_distribution.get) if hour_distribution else None,
            'peak_payment_day': max(day_distribution, key=day_distribution.get) if day_distribution else None,
            'hourly_distribution': hour_distribution,
            'daily_distribution': day_distribution
        }
    
    async def _analyze_behavioral_patterns(self, payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Analyze customer payment behaviors"""
        first_time_customers = len([p for p in payments if p.is_first_payment])
        recurring_customers = len([p for p in payments if not p.is_first_payment])
        
        return {
            'first_time_vs_returning': {
                'first_time': first_time_customers,
                'returning': recurring_customers
            },
            'discount_usage_rate': len([p for p in payments if p.discount_amount > 0]) / len(payments) * 100 if payments else 0,
            'average_time_between_payments': self._calculate_avg_time_between_payments(payments)
        }
    
    def _calculate_avg_time_between_payments(self, payments: List[PaymentSummary]) -> float:
        """Calculate average time between payments for returning customers"""
        customer_payments = {}
        
        for payment in payments:
            if payment.user_id not in customer_payments:
                customer_payments[payment.user_id] = []
            customer_payments[payment.user_id].append(payment.payment_date)
        
        time_gaps = []
        for user_id, payment_dates in customer_payments.items():
            if len(payment_dates) > 1:
                sorted_dates = sorted(payment_dates)
                for i in range(1, len(sorted_dates)):
                    gap = (sorted_dates[i] - sorted_dates[i-1]).days
                    time_gaps.append(gap)
        
        return np.mean(time_gaps) if time_gaps else 0
    
    async def _analyze_risk_patterns(self, payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Analyze payment risk patterns"""
        high_risk_payments = [p for p in payments if p.risk_score and p.risk_score >= 0.7]
        fraud_indicators = [p for p in payments if p.fraud_indicators]
        
        return {
            'high_risk_payment_count': len(high_risk_payments),
            'fraud_indicator_count': len(fraud_indicators),
            'average_risk_score': np.mean([p.risk_score for p in payments if p.risk_score]),
            'risk_distribution': self._calculate_risk_distribution(payments)
        }
    
    def _calculate_risk_distribution(self, payments: List[PaymentSummary]) -> Dict[str, int]:
        """Calculate distribution of risk scores"""
        risk_buckets = {'low': 0, 'medium': 0, 'high': 0, 'unknown': 0}
        
        for payment in payments:
            if not payment.risk_score:
                risk_buckets['unknown'] += 1
            elif payment.risk_score < 0.3:
                risk_buckets['low'] += 1
            elif payment.risk_score < 0.7:
                risk_buckets['medium'] += 1
            else:
                risk_buckets['high'] += 1
        
        return risk_buckets
    
    async def _analyze_conversion_patterns(self, payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Analyze payment conversion patterns"""
        # This would typically analyze the full conversion funnel
        # For now, return basic conversion metrics
        total_attempts = len(payments)
        successful_payments = len([p for p in payments if p.status == 'completed'])
        
        return {
            'conversion_rate': (successful_payments / total_attempts * 100) if total_attempts > 0 else 0,
            'total_attempts': total_attempts,
            'successful_payments': successful_payments,
            'abandonment_rate': ((total_attempts - successful_payments) / total_attempts * 100) if total_attempts > 0 else 0
        }
    
    def _calculate_subscription_retention(self, subscription_groups: Dict[str, List[PaymentSummary]]) -> float:
        """Calculate subscription retention rate"""
        current_date = datetime.utcnow()
        active_subscriptions = 0
        
        for sub_id, payments in subscription_groups.items():
            latest_payment = max(payments, key=lambda x: x.payment_date)
            if latest_payment.next_payment_date and latest_payment.next_payment_date > current_date:
                active_subscriptions += 1
        
        return (active_subscriptions / len(subscription_groups) * 100) if subscription_groups else 0
    
    def _calculate_subscription_churn(self, subscription_groups: Dict[str, List[PaymentSummary]]) -> float:
        """Calculate subscription churn rate"""
        retention_rate = self._calculate_subscription_retention(subscription_groups)
        return 100 - retention_rate
    
    def _analyze_subscription_changes(self, subscription_groups: Dict[str, List[PaymentSummary]]) -> Dict[str, Any]:
        """Analyze subscription upgrades and downgrades"""
        changes = {'upgrades': 0, 'downgrades': 0, 'no_change': 0}
        
        for sub_id, payments in subscription_groups.items():
            if len(payments) > 1:
                sorted_payments = sorted(payments, key=lambda x: x.payment_date)
                
                for i in range(1, len(sorted_payments)):
                    prev_amount = sorted_payments[i-1].amount
                    curr_amount = sorted_payments[i].amount
                    
                    if curr_amount > prev_amount:
                        changes['upgrades'] += 1
                    elif curr_amount < prev_amount:
                        changes['downgrades'] += 1
                    else:
                        changes['no_change'] += 1
        
        return changes
    
    def _analyze_billing_cycles(self, subscriptions: List[PaymentSummary]) -> Dict[str, int]:
        """Analyze billing cycle distribution"""
        cycle_distribution = {}
        
        for subscription in subscriptions:
            cycle = subscription.billing_cycle or 'unknown'
            cycle_distribution[cycle] = cycle_distribution.get(cycle, 0) + 1
        
        return cycle_distribution
    
    def _analyze_failure_reasons(self, failed_payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Analyze reasons for payment failures"""
        # This would typically extract failure reasons from payment processor responses
        # For now, return placeholder analysis
        return {
            'insufficient_funds': len(failed_payments) * 0.4,  # Estimated distribution
            'card_declined': len(failed_payments) * 0.3,
            'technical_errors': len(failed_payments) * 0.2,
            'other': len(failed_payments) * 0.1
        }
    
    def _analyze_failures_by_method(self, failed_payments: List[PaymentSummary]) -> Dict[str, int]:
        """Analyze failures by payment method"""
        method_failures = {}
        
        for payment in failed_payments:
            method = payment.payment_method
            method_failures[method] = method_failures.get(method, 0) + 1
        
        return method_failures
    
    def _analyze_failure_patterns(self, failed_payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Analyze failure patterns"""
        # Time-based failure analysis
        hour_failures = {}
        day_failures = {}
        
        for payment in failed_payments:
            hour = payment.payment_date.hour
            day = payment.payment_date.strftime('%A')
            
            hour_failures[hour] = hour_failures.get(hour, 0) + 1
            day_failures[day] = day_failures.get(day, 0) + 1
        
        return {
            'peak_failure_hour': max(hour_failures, key=hour_failures.get) if hour_failures else None,
            'peak_failure_day': max(day_failures, key=day_failures.get) if day_failures else None,
            'hourly_failure_distribution': hour_failures,
            'daily_failure_distribution': day_failures
        }
    
    def _identify_recovery_opportunities(self, failed_payments: List[PaymentSummary]) -> Dict[str, Any]:
        """Identify opportunities to recover failed payments"""
        recoverable_amount = sum(p.amount for p in failed_payments)
        
        # Analyze failure timing - recent failures have higher recovery potential
        current_date = datetime.utcnow()
        recent_failures = [
            p for p in failed_payments 
            if (current_date - p.payment_date).days <= 30
        ]
        
        return {
            'total_recoverable_amount': recoverable_amount,
            'recent_failures_count': len(recent_failures),
            'recent_recoverable_amount': sum(p.amount for p in recent_failures),
            'recovery_rate_estimate': 0.25  # Estimated 25% recovery rate
        }
    
    def _generate_failure_prevention_recommendations(self, failed_payments: List[PaymentSummary]) -> List[str]:
        """Generate recommendations to prevent payment failures"""
        recommendations = []
        
        # Analyze common failure patterns
        method_failures = self._analyze_failures_by_method(failed_payments)
        most_problematic_method = max(method_failures, key=method_failures.get) if method_failures else None
        
        if most_problematic_method:
            recommendations.append(f"Review and improve {most_problematic_method} payment processing")
        
        if len(failed_payments) > 10:
            recommendations.append("Implement retry logic for failed payments")
            recommendations.append("Add payment method fallback options")
            recommendations.append("Implement real-time payment validation")
        
        return recommendations