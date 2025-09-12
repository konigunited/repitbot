"""
PyTest Configuration and Fixtures for RepitBot Microservices Testing
===================================================================
"""

import pytest
import asyncio
import aiohttp
import json
import time
import random
import string
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import jwt

# Test Configuration
@dataclass
class TestConfig:
    """Central test configuration"""
    # Service URLs
    API_GATEWAY_URL = "http://localhost:8000"
    USER_SERVICE_URL = "http://localhost:8001"
    LESSON_SERVICE_URL = "http://localhost:8002"
    HOMEWORK_SERVICE_URL = "http://localhost:8003"
    PAYMENT_SERVICE_URL = "http://localhost:8004"
    MATERIAL_SERVICE_URL = "http://localhost:8005"
    NOTIFICATION_SERVICE_URL = "http://localhost:8006"
    ANALYTICS_SERVICE_URL = "http://localhost:8007"
    STUDENT_SERVICE_URL = "http://localhost:8008"
    
    # Infrastructure URLs
    PROMETHEUS_URL = "http://localhost:9090"
    GRAFANA_URL = "http://localhost:3000"
    RABBITMQ_MANAGEMENT_URL = "http://localhost:15672"
    
    # Test credentials
    JWT_SECRET = "your-super-secret-jwt-key-change-in-production"
    ADMIN_EMAIL = "admin@repitbot.com"
    ADMIN_PASSWORD = "admin123"
    
    # Test timeouts
    REQUEST_TIMEOUT = 30
    HEALTH_CHECK_TIMEOUT = 10
    INTEGRATION_TIMEOUT = 60
    
    # Performance thresholds
    MAX_RESPONSE_TIME_MS = 1000
    LOAD_TEST_CONCURRENT_USERS = 100
    LOAD_TEST_DURATION = 60


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def http_client():
    """HTTP client for making requests to services"""
    timeout = aiohttp.ClientTimeout(total=TestConfig.REQUEST_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        yield session


@pytest.fixture(scope="session")
def test_config():
    """Test configuration instance"""
    return TestConfig()


@pytest.fixture
def generate_test_user():
    """Generate unique test user data"""
    def _generate(role: str = "STUDENT") -> Dict[str, Any]:
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return {
            "email": f"test_{role.lower()}_{random_suffix}@test.com",
            "password": "Test123!",
            "name": f"Test {role.title()} {random_suffix}",
            "role": role,
            "telegram_id": random.randint(100000000, 999999999),
            "phone": f"+7912{random.randint(1000000, 9999999)}",
            "grade": random.randint(1, 11) if role == "STUDENT" else None,
            "subjects": ["математика", "физика"] if role in ["STUDENT", "TUTOR"] else None
        }
    return _generate


@pytest.fixture
async def auth_tokens(http_client, test_config, generate_test_user):
    """Generate JWT tokens for different roles"""
    tokens = {}
    
    for role in ["PARENT", "STUDENT", "TUTOR"]:
        # Create test user
        user_data = generate_test_user(role)
        
        # Register user through API Gateway
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/auth/register",
            json=user_data
        ) as response:
            if response.status == 201:
                user_response = await response.json()
                
                # Login to get token
                async with http_client.post(
                    f"{test_config.API_GATEWAY_URL}/api/v1/auth/login",
                    json={
                        "email": user_data["email"],
                        "password": user_data["password"]
                    }
                ) as login_response:
                    if login_response.status == 200:
                        login_data = await login_response.json()
                        tokens[role] = {
                            "token": login_data["access_token"],
                            "user": user_response,
                            "headers": {"Authorization": f"Bearer {login_data['access_token']}"}
                        }
    
    return tokens


@pytest.fixture
def auth_headers():
    """Generate authorization headers"""
    def _headers(token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    return _headers


@pytest.fixture
async def health_checker(http_client, test_config):
    """Service health checker"""
    async def _check_service_health(service_url: str, timeout: int = 10) -> Dict[str, Any]:
        try:
            async with http_client.get(
                f"{service_url}/health", 
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                status_code = response.status
                response_time = response.headers.get('X-Response-Time', 'unknown')
                
                if status_code == 200:
                    health_data = await response.json()
                    return {
                        "status": "healthy",
                        "status_code": status_code,
                        "response_time": response_time,
                        "details": health_data
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "status_code": status_code,
                        "response_time": response_time,
                        "error": await response.text()
                    }
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "error": f"Health check timeout after {timeout}s"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    return _check_service_health


@pytest.fixture
def test_lesson_data():
    """Generate test lesson data"""
    def _generate() -> Dict[str, Any]:
        return {
            "title": f"Test Lesson {random.randint(1000, 9999)}",
            "description": "Test lesson description",
            "subject": "математика",
            "grade": random.randint(1, 11),
            "scheduled_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "duration_minutes": 60,
            "price": 1000.0,
            "type": "individual"
        }
    return _generate


@pytest.fixture
def test_homework_data():
    """Generate test homework data"""
    def _generate(lesson_id: int) -> Dict[str, Any]:
        return {
            "lesson_id": lesson_id,
            "title": f"Test Homework {random.randint(1000, 9999)}",
            "description": "Complete the math exercises from pages 45-50",
            "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "max_score": 100,
            "subject": "математика"
        }
    return _generate


@pytest.fixture
def test_payment_data():
    """Generate test payment data"""
    def _generate() -> Dict[str, Any]:
        return {
            "amount": random.uniform(500.0, 5000.0),
            "payment_method": "card",
            "description": "Test payment for lessons"
        }
    return _generate


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during tests"""
    metrics = []
    
    def _record_metric(operation: str, duration_ms: float, success: bool = True):
        metrics.append({
            "operation": operation,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
    
    def _get_metrics():
        return metrics.copy()
    
    def _reset_metrics():
        metrics.clear()
    
    return {
        "record": _record_metric,
        "get_metrics": _get_metrics,
        "reset": _reset_metrics
    }


@pytest.fixture
async def database_cleaner():
    """Clean up test data after tests"""
    created_resources = []
    
    def _track_resource(resource_type: str, resource_id: Any):
        created_resources.append({
            "type": resource_type,
            "id": resource_id
        })
    
    yield _track_resource
    
    # Cleanup after test
    # This would connect to services and clean up created test data
    # Implementation depends on service APIs
    print(f"Cleaning up {len(created_resources)} test resources")


@pytest.fixture
def event_publisher():
    """Mock event publisher for testing event flows"""
    published_events = []
    
    def _publish_event(event_type: str, event_data: Dict[str, Any]):
        event = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.now().isoformat(),
            "event_id": str(random.randint(100000, 999999))
        }
        published_events.append(event)
        return event
    
    def _get_published_events():
        return published_events.copy()
    
    def _clear_events():
        published_events.clear()
    
    return {
        "publish": _publish_event,
        "get_events": _get_published_events,
        "clear": _clear_events
    }


# Test markers for categorization
pytest.mark.infrastructure = pytest.mark.infrastructure
pytest.mark.auth = pytest.mark.auth
pytest.mark.functional = pytest.mark.functional
pytest.mark.contract = pytest.mark.contract
pytest.mark.events = pytest.mark.events
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.chaos = pytest.mark.chaos
pytest.mark.monitoring = pytest.mark.monitoring


# Global test hooks
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "infrastructure: Infrastructure and health check tests"
    )
    config.addinivalue_line(
        "markers", "auth: Authentication and authorization tests"
    )
    config.addinivalue_line(
        "markers", "functional: Functional tests per role"
    )
    config.addinivalue_line(
        "markers", "contract: Contract testing between services"
    )
    config.addinivalue_line(
        "markers", "events: Event-driven architecture tests"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "security: Security and vulnerability tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "chaos: Chaos engineering tests"
    )
    config.addinivalue_line(
        "markers", "monitoring: Monitoring and observability tests"
    )


def pytest_sessionstart(session):
    """Actions before test session starts"""
    print("\n" + "="*80)
    print("🧪 RepitBot Microservices Test Suite Starting")
    print("="*80)
    print(f"Test session started at: {datetime.now()}")
    print("Services to test:")
    print("  - API Gateway (8000)")
    print("  - User Service (8001)")
    print("  - Lesson Service (8002)")
    print("  - Homework Service (8003)")
    print("  - Payment Service (8004)")
    print("  - Material Service (8005)")
    print("  - Notification Service (8006)")
    print("  - Analytics Service (8007)")
    print("  - Student Service (8008)")
    print("  - Infrastructure (PostgreSQL, RabbitMQ, Redis)")
    print("  - Monitoring (Prometheus, Grafana)")
    print("="*80 + "\n")


def pytest_sessionfinish(session, exitstatus):
    """Actions after test session finishes"""
    print("\n" + "="*80)
    print("🏁 RepitBot Microservices Test Suite Completed")
    print("="*80)
    print(f"Test session finished at: {datetime.now()}")
    print(f"Exit status: {exitstatus}")
    if exitstatus == 0:
        print("✅ All tests passed successfully!")
    else:
        print("❌ Some tests failed. Check the reports above.")
    print("="*80 + "\n")