# -*- coding: utf-8 -*-
"""
Shared configuration package for RepitBot microservices.

This package provides configuration management including:
- Base settings classes
- Service-specific settings
- Environment-specific configurations
- Settings factories and utilities
"""

from .base_settings import (
    # Base settings
    BaseServiceSettings,
    DevelopmentSettings,
    ProductionSettings,
    TestingSettings,
    
    # Service-specific settings
    UserServiceSettings,
    AuthServiceSettings,
    LessonServiceSettings,
    HomeworkServiceSettings,
    PaymentServiceSettings,
    NotificationServiceSettings,
    MaterialServiceSettings,
    AnalyticsServiceSettings,
    AchievementServiceSettings,
    SchedulerServiceSettings,
    
    # Utilities
    get_settings_class,
    get_settings,
)

__all__ = [
    # Base settings
    "BaseServiceSettings",
    "DevelopmentSettings", 
    "ProductionSettings",
    "TestingSettings",
    
    # Service-specific settings
    "UserServiceSettings",
    "AuthServiceSettings",
    "LessonServiceSettings", 
    "HomeworkServiceSettings",
    "PaymentServiceSettings",
    "NotificationServiceSettings",
    "MaterialServiceSettings",
    "AnalyticsServiceSettings",
    "AchievementServiceSettings",
    "SchedulerServiceSettings",
    
    # Utilities
    "get_settings_class",
    "get_settings",
]