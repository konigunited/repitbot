"""
RepitBot Microservices Test Suite
=================================

Comprehensive testing framework for RepitBot microservices architecture.
Covers all aspects from infrastructure health checks to end-to-end scenarios.

Test Categories:
- Infrastructure Tests (health checks, connectivity)
- Authentication & Authorization Tests (JWT, RBAC)
- Functional Tests (per role: Parent, Student, Tutor)
- Contract Tests (API contracts between services)
- Event-Driven Tests (RabbitMQ message flows)
- Performance Tests (load, stress, volume)
- Security Tests (vulnerabilities, penetration)
- Integration Tests (database, external services)
- E2E Tests (complete user journeys)
- Chaos Engineering (resilience, fault tolerance)
- Monitoring Tests (observability stack)

Services Under Test:
- API Gateway (8000)
- User Service (8001) 
- Lesson Service (8002)
- Homework Service (8003)
- Payment Service (8004)
- Material Service (8005)
- Notification Service (8006)
- Analytics Service (8007)
- Student Service (8008)
- Telegram Bot (integrated with microservices)

Infrastructure:
- PostgreSQL (separate DBs per service)
- RabbitMQ (event bus)
- Redis (caching)
- Prometheus (metrics)
- Grafana (dashboards)

Roles:
- PARENT: payments, schedule, child progress monitoring
- STUDENT: lessons, homework, materials, achievements
- TUTOR: lesson management, grading, analytics, materials
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

__version__ = "1.0.0"
__author__ = "RepitBot QA Team"