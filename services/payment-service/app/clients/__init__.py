# -*- coding: utf-8 -*-
"""
HTTP Clients for inter-service communication
"""

from .user_client import UserServiceClient
from .lesson_client import LessonServiceClient
from .base_client import BaseServiceClient, ServiceClientError

__all__ = [
    'UserServiceClient',
    'LessonServiceClient', 
    'BaseServiceClient',
    'ServiceClientError'
]