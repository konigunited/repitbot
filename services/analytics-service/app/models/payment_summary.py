from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class PaymentSummary(Base):
    """Payment analytics and financial metrics"""
    __tablename__ = "payment_summary"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    tutor_id = Column(String, nullable=True, index=True)
    
    # Основная информация о платеже
    amount = Column(Float, nullable=False)
    currency = Column(String, default='RUB')
    payment_method = Column(String, nullable=False)  # card, bank_transfer, cash, etc.
    payment_date = Column(DateTime, nullable=False, index=True)
    
    # Статус и обработка
    status = Column(String, nullable=False)  # pending, completed, failed, refunded, cancelled
    processing_time = Column(Integer, nullable=True)  # время обработки в секундах
    confirmation_time = Column(DateTime, nullable=True)
    
    # Детали транзакции
    transaction_id = Column(String, nullable=True)
    external_payment_id = Column(String, nullable=True)  # ID в платежной системе
    merchant_id = Column(String, nullable=True)
    
    # Типы платежей и услуги
    payment_type = Column(String, nullable=False)  # lesson, subscription, materials, etc.
    service_details = Column(JSON, nullable=True)  # детали оплаченной услуги
    lesson_ids = Column(JSON, nullable=True)  # связанные уроки
    
    # Ценообразование
    base_price = Column(Float, nullable=True)
    discount_amount = Column(Float, default=0.0)
    discount_percentage = Column(Float, default=0.0)
    discount_code = Column(String, nullable=True)
    tax_amount = Column(Float, default=0.0)
    fee_amount = Column(Float, default=0.0)  # комиссия платежной системы
    
    # Подписки и повторяющиеся платежи
    is_recurring = Column(Boolean, default=False)
    subscription_id = Column(String, nullable=True)
    billing_cycle = Column(String, nullable=True)  # weekly, monthly, etc.
    next_payment_date = Column(DateTime, nullable=True)
    
    # География и локализация
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    city = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    
    # Устройство и платформа
    device_type = Column(String, nullable=True)  # mobile, desktop, tablet
    browser = Column(String, nullable=True)
    platform = Column(String, nullable=True)  # ios, android, web
    
    # Маркетинг и источники
    referral_source = Column(String, nullable=True)
    campaign_id = Column(String, nullable=True)
    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)
    
    # Клиентская активность
    is_first_payment = Column(Boolean, default=False)
    customer_lifetime_value = Column(Float, nullable=True)
    previous_payments_count = Column(Integer, default=0)
    days_since_last_payment = Column(Integer, nullable=True)
    
    # Риск и безопасность
    risk_score = Column(Float, nullable=True)  # 0-1, где 1 = высокий риск
    fraud_indicators = Column(JSON, nullable=True)
    security_checks = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    
    # Возвраты и отмены
    refund_amount = Column(Float, default=0.0)
    refund_date = Column(DateTime, nullable=True)
    refund_reason = Column(String, nullable=True)
    chargeback_amount = Column(Float, default=0.0)
    chargeback_date = Column(DateTime, nullable=True)
    
    # Коммуникации
    receipt_sent = Column(Boolean, default=False)
    receipt_email = Column(String, nullable=True)
    confirmation_sent = Column(Boolean, default=False)
    followup_required = Column(Boolean, default=False)
    
    # Аналитические метрики
    payment_velocity = Column(Float, nullable=True)  # время от начала до завершения покупки
    cart_abandonment_recovery = Column(Boolean, default=False)
    upsell_amount = Column(Float, default=0.0)
    cross_sell_amount = Column(Float, default=0.0)
    
    # Качество обслуживания
    customer_satisfaction = Column(Float, nullable=True)  # 1-5
    support_interactions = Column(Integer, default=0)
    issues_reported = Column(JSON, nullable=True)
    
    # Временные метрики
    hour_of_day = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    week_of_year = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    quarter = Column(Integer, nullable=True)
    
    # Партнерство и комиссии
    partner_id = Column(String, nullable=True)
    affiliate_commission = Column(Float, default=0.0)
    tutor_commission = Column(Float, default=0.0)
    platform_fee = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PaymentSummary(payment_id={self.payment_id}, amount={self.amount}, status={self.status})>"

    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'user_id': self.user_id,
            'tutor_id': self.tutor_id,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'status': self.status,
            'payment_type': self.payment_type,
            'discount_amount': self.discount_amount,
            'is_recurring': self.is_recurring,
            'is_first_payment': self.is_first_payment,
            'risk_score': self.risk_score,
            'refund_amount': self.refund_amount
        }

    def get_net_amount(self) -> float:
        """Calculate net amount after all deductions"""
        return self.amount - self.fee_amount - self.refund_amount - self.chargeback_amount

    def get_profit_margin(self) -> float:
        """Calculate profit margin percentage"""
        if self.amount <= 0:
            return 0.0
            
        total_costs = (
            self.fee_amount + 
            self.tutor_commission + 
            self.affiliate_commission + 
            self.platform_fee
        )
        
        profit = self.amount - total_costs
        return (profit / self.amount) * 100

    def is_high_value_transaction(self, threshold: float = 5000.0) -> bool:
        """Check if this is a high-value transaction"""
        return self.amount >= threshold

    def get_payment_risk_level(self) -> str:
        """Determine payment risk level based on various factors"""
        if not self.risk_score:
            return 'unknown'
            
        if self.risk_score >= 0.8:
            return 'high'
        elif self.risk_score >= 0.5:
            return 'medium'
        else:
            return 'low'

    def calculate_customer_value_score(self) -> float:
        """Calculate customer value score for this transaction"""
        score = 0.0
        
        # Amount contribution (40%)
        if self.amount:
            score += min(self.amount / 10000 * 40, 40)  # normalize to 10k max
        
        # Loyalty factor (30%)
        if self.previous_payments_count:
            score += min(self.previous_payments_count * 2, 30)
        
        # Payment reliability (20%)
        if self.status == 'completed':
            score += 20
        elif self.status == 'pending':
            score += 10
            
        # Risk factor (10%)
        if self.risk_score:
            score += (1 - self.risk_score) * 10
        
        return min(score, 100.0)

    def get_seasonality_indicators(self) -> dict:
        """Get seasonality indicators for this payment"""
        return {
            'is_weekend': self.day_of_week in [5, 6] if self.day_of_week else None,
            'is_evening': self.hour_of_day >= 18 if self.hour_of_day else None,
            'is_holiday_season': self.month in [11, 12] if self.month else None,
            'is_back_to_school': self.month in [8, 9] if self.month else None,
            'quarter': f'Q{self.quarter}' if self.quarter else None
        }