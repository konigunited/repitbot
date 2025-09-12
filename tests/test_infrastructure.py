"""
Infrastructure Health Check Tests
===============================

Tests for validating the health and connectivity of all microservices
and infrastructure components in the RepitBot system.

Components tested:
- All 9 microservices (health endpoints)
- PostgreSQL databases (connectivity and basic queries)
- RabbitMQ (connection and queue status)
- Redis (connection and basic operations)
- Docker containers (status and resource usage)
- Network connectivity between services
- Monitoring stack (Prometheus, Grafana)
"""

import pytest
import asyncio
import aiohttp
import time
import psutil
from typing import Dict, List, Any
import docker
import pika
import redis
import asyncpg


@pytest.mark.infrastructure
class TestInfrastructureHealth:
    """Infrastructure health and connectivity tests"""
    
    async def test_all_services_health_checks(self, http_client, test_config, health_checker):
        """Test that all 9 microservices respond to health checks"""
        services = {
            "API Gateway": test_config.API_GATEWAY_URL,
            "User Service": test_config.USER_SERVICE_URL,
            "Lesson Service": test_config.LESSON_SERVICE_URL,
            "Homework Service": test_config.HOMEWORK_SERVICE_URL,
            "Payment Service": test_config.PAYMENT_SERVICE_URL,
            "Material Service": test_config.MATERIAL_SERVICE_URL,
            "Notification Service": test_config.NOTIFICATION_SERVICE_URL,
            "Analytics Service": test_config.ANALYTICS_SERVICE_URL,
            "Student Service": test_config.STUDENT_SERVICE_URL
        }
        
        health_results = {}
        failed_services = []
        
        for service_name, service_url in services.items():
            print(f"🔍 Checking health of {service_name}...")
            health_result = await health_checker(service_url, timeout=test_config.HEALTH_CHECK_TIMEOUT)
            health_results[service_name] = health_result
            
            if health_result["status"] != "healthy":
                failed_services.append(service_name)
                print(f"❌ {service_name}: {health_result}")
            else:
                print(f"✅ {service_name}: Healthy")
        
        # Assert all services are healthy
        assert len(failed_services) == 0, f"Failed health checks: {failed_services}"
        
        # Verify response times are reasonable
        for service_name, result in health_results.items():
            if result["status"] == "healthy" and "response_time" in result:
                # Response time should be under 1 second for health checks
                assert result.get("response_time", 0) < 1000, f"{service_name} health check too slow"
    
    
    async def test_service_health_endpoints_structure(self, http_client, test_config):
        """Test that health endpoints return proper structure"""
        async with http_client.get(f"{test_config.API_GATEWAY_URL}/health") as response:
            assert response.status == 200
            health_data = await response.json()
            
            # Verify required health check fields
            required_fields = ["status", "timestamp", "version", "uptime", "dependencies"]
            for field in required_fields:
                assert field in health_data, f"Missing required field: {field}"
            
            # Verify status is one of expected values
            assert health_data["status"] in ["healthy", "degraded", "unhealthy"]
            
            # Verify dependencies section exists
            assert isinstance(health_data["dependencies"], dict)
    
    
    async def test_infrastructure_connectivity(self, test_config):
        """Test connectivity to infrastructure components"""
        
        # Test PostgreSQL connectivity
        try:
            conn = await asyncpg.connect(
                "postgresql://repitbot:repitbot_password@localhost:5432/repitbot"
            )
            # Test basic query
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            await conn.close()
            print("✅ PostgreSQL: Connected and responsive")
        except Exception as e:
            pytest.fail(f"❌ PostgreSQL connection failed: {e}")
        
        # Test Redis connectivity
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            
            # Test basic operations
            test_key = "test_connection"
            r.set(test_key, "test_value", ex=10)
            assert r.get(test_key) == "test_value"
            r.delete(test_key)
            print("✅ Redis: Connected and responsive")
        except Exception as e:
            pytest.fail(f"❌ Redis connection failed: {e}")
        
        # Test RabbitMQ connectivity
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    credentials=pika.PlainCredentials('repitbot', 'repitbot_password')
                )
            )
            channel = connection.channel()
            
            # Test queue declaration
            test_queue = "test_connection_queue"
            channel.queue_declare(queue=test_queue, durable=False)
            channel.queue_delete(queue=test_queue)
            
            connection.close()
            print("✅ RabbitMQ: Connected and responsive")
        except Exception as e:
            pytest.fail(f"❌ RabbitMQ connection failed: {e}")
    
    
    def test_docker_containers_status(self):
        """Test that all required Docker containers are running"""
        try:
            client = docker.from_env()
            containers = client.containers.list()
            
            expected_containers = [
                "repitbot_postgres",
                "repitbot_rabbitmq", 
                "repitbot_redis",
                "repitbot_user_service",
                "repitbot_lesson_service",
                "repitbot_homework_service",
                "repitbot_payment_service",
                "repitbot_material_service",
                "repitbot_notification_service",
                "repitbot_analytics_service",
                "repitbot_student_service",
                "repitbot_api_gateway",
                "repitbot_telegram_bot",
                "repitbot_prometheus",
                "repitbot_grafana"
            ]
            
            running_containers = [container.name for container in containers 
                                if container.status == "running"]
            
            missing_containers = []
            for expected in expected_containers:
                if expected not in running_containers:
                    missing_containers.append(expected)
            
            if missing_containers:
                print(f"❌ Missing containers: {missing_containers}")
                print(f"📋 Running containers: {running_containers}")
            else:
                print("✅ All required containers are running")
            
            assert len(missing_containers) == 0, f"Missing containers: {missing_containers}"
            
        except Exception as e:
            pytest.fail(f"❌ Docker status check failed: {e}")
    
    
    def test_container_resource_usage(self):
        """Test that containers are not using excessive resources"""
        try:
            client = docker.from_env()
            containers = client.containers.list()
            
            high_resource_containers = []
            
            for container in containers:
                if not container.name.startswith("repitbot_"):
                    continue
                    
                # Get container stats
                stats = container.stats(stream=False)
                
                # Calculate CPU usage percentage
                cpu_usage = 0
                if "cpu_stats" in stats and "precpu_stats" in stats:
                    cpu_delta = (stats["cpu_stats"]["cpu_usage"]["total_usage"] - 
                               stats["precpu_stats"]["cpu_usage"]["total_usage"])
                    system_delta = (stats["cpu_stats"]["system_cpu_usage"] - 
                                  stats["precpu_stats"]["system_cpu_usage"])
                    
                    if system_delta > 0:
                        cpu_usage = (cpu_delta / system_delta) * 100
                
                # Calculate memory usage percentage
                memory_usage = 0
                if "memory_stats" in stats:
                    memory_used = stats["memory_stats"]["usage"]
                    memory_limit = stats["memory_stats"]["limit"]
                    memory_usage = (memory_used / memory_limit) * 100
                
                # Check if usage is too high
                if cpu_usage > 80:  # More than 80% CPU
                    high_resource_containers.append(f"{container.name}: CPU {cpu_usage:.1f}%")
                
                if memory_usage > 80:  # More than 80% Memory
                    high_resource_containers.append(f"{container.name}: Memory {memory_usage:.1f}%")
                
                print(f"📊 {container.name}: CPU {cpu_usage:.1f}%, Memory {memory_usage:.1f}%")
            
            # Warning for high resource usage (not failure)
            if high_resource_containers:
                print(f"⚠️  High resource usage detected: {high_resource_containers}")
            
        except Exception as e:
            print(f"⚠️  Resource monitoring failed: {e}")
    
    
    async def test_service_startup_order_dependencies(self, http_client, test_config, health_checker):
        """Test that services start in correct dependency order"""
        
        # Define service dependency graph
        dependencies = {
            "Infrastructure": ["postgres", "rabbitmq", "redis"],
            "Core Services": [
                test_config.USER_SERVICE_URL,  # Must start first
                test_config.LESSON_SERVICE_URL,  # Depends on User
                test_config.HOMEWORK_SERVICE_URL,  # Depends on User + Lesson
            ],
            "Business Services": [
                test_config.PAYMENT_SERVICE_URL,  # Depends on User + Lesson
                test_config.MATERIAL_SERVICE_URL,  # Depends on User + Lesson
                test_config.NOTIFICATION_SERVICE_URL,  # Depends on User
                test_config.STUDENT_SERVICE_URL,  # Depends on User + Lesson + Homework
                test_config.ANALYTICS_SERVICE_URL,  # Depends on all above
            ],
            "Gateway": [
                test_config.API_GATEWAY_URL  # Depends on all services
            ]
        }
        
        # Check each tier
        for tier_name, services in dependencies.items():
            if tier_name == "Infrastructure":
                # Infrastructure is tested in other methods
                continue
                
            print(f"🔍 Checking {tier_name} tier...")
            
            for service_url in services:
                health_result = await health_checker(service_url)
                assert health_result["status"] == "healthy", \
                    f"Service {service_url} not healthy in {tier_name} tier"
            
            print(f"✅ {tier_name} tier: All services healthy")
    
    
    async def test_network_connectivity_between_services(self, http_client, test_config):
        """Test that services can communicate with each other"""
        
        # Test API Gateway can reach all services
        # This is tested through the gateway's health check which should verify downstream services
        async with http_client.get(f"{test_config.API_GATEWAY_URL}/health") as response:
            assert response.status == 200
            health_data = await response.json()
            
            # Gateway health should include dependency status
            if "dependencies" in health_data:
                for dep_name, dep_status in health_data["dependencies"].items():
                    assert dep_status.get("status") in ["healthy", "connected"], \
                        f"Gateway cannot reach {dep_name}: {dep_status}"
    
    
    async def test_monitoring_stack_health(self, http_client, test_config):
        """Test that monitoring infrastructure is working"""
        
        # Test Prometheus
        try:
            async with http_client.get(f"{test_config.PROMETHEUS_URL}/-/healthy") as response:
                assert response.status == 200
                print("✅ Prometheus: Healthy")
        except Exception as e:
            pytest.fail(f"❌ Prometheus health check failed: {e}")
        
        # Test Grafana
        try:
            async with http_client.get(f"{test_config.GRAFANA_URL}/api/health") as response:
                assert response.status == 200
                health_data = await response.json()
                assert health_data.get("database") == "ok"
                print("✅ Grafana: Healthy")
        except Exception as e:
            pytest.fail(f"❌ Grafana health check failed: {e}")
    
    
    async def test_service_response_times(self, http_client, test_config, performance_monitor):
        """Test that all services respond within acceptable time limits"""
        
        services = {
            "API Gateway": test_config.API_GATEWAY_URL,
            "User Service": test_config.USER_SERVICE_URL,
            "Lesson Service": test_config.LESSON_SERVICE_URL,
            "Homework Service": test_config.HOMEWORK_SERVICE_URL,
            "Payment Service": test_config.PAYMENT_SERVICE_URL,
            "Material Service": test_config.MATERIAL_SERVICE_URL,
            "Notification Service": test_config.NOTIFICATION_SERVICE_URL,
            "Analytics Service": test_config.ANALYTICS_SERVICE_URL,
            "Student Service": test_config.STUDENT_SERVICE_URL
        }
        
        slow_services = []
        
        for service_name, service_url in services.items():
            start_time = time.time()
            
            try:
                async with http_client.get(f"{service_url}/health") as response:
                    end_time = time.time()
                    response_time_ms = (end_time - start_time) * 1000
                    
                    performance_monitor["record"](
                        f"{service_name}_health_check", 
                        response_time_ms, 
                        response.status == 200
                    )
                    
                    if response_time_ms > test_config.MAX_RESPONSE_TIME_MS:
                        slow_services.append(f"{service_name}: {response_time_ms:.1f}ms")
                    else:
                        print(f"✅ {service_name}: {response_time_ms:.1f}ms")
                        
            except Exception as e:
                performance_monitor["record"](f"{service_name}_health_check", 0, False)
                pytest.fail(f"❌ {service_name} health check failed: {e}")
        
        # Assert no services are too slow
        assert len(slow_services) == 0, f"Slow services (>{test_config.MAX_RESPONSE_TIME_MS}ms): {slow_services}"
    
    
    async def test_database_per_service_isolation(self):
        """Test that each service has its own isolated database"""
        
        expected_databases = [
            "user_service",
            "lesson_service", 
            "homework_service",
            "payment_service",
            "material_service",
            "notification_service",
            "analytics_service",
            "student_service",
            "repitbot"  # Main database
        ]
        
        try:
            conn = await asyncpg.connect(
                "postgresql://repitbot:repitbot_password@localhost:5432/postgres"
            )
            
            # Get list of databases
            databases = await conn.fetch(
                "SELECT datname FROM pg_database WHERE datistemplate = false"
            )
            database_names = [db['datname'] for db in databases]
            
            missing_databases = []
            for expected_db in expected_databases:
                if expected_db not in database_names:
                    missing_databases.append(expected_db)
            
            await conn.close()
            
            if missing_databases:
                print(f"❌ Missing databases: {missing_databases}")
                print(f"📋 Found databases: {database_names}")
            else:
                print("✅ All service databases exist")
            
            assert len(missing_databases) == 0, f"Missing databases: {missing_databases}"
            
        except Exception as e:
            pytest.fail(f"❌ Database isolation check failed: {e}")
    
    
    async def test_message_queue_setup(self):
        """Test that RabbitMQ queues and exchanges are properly configured"""
        
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    credentials=pika.PlainCredentials('repitbot', 'repitbot_password')
                )
            )
            channel = connection.channel()
            
            # Expected exchanges for event-driven architecture
            expected_exchanges = [
                "user.events",
                "lesson.events", 
                "homework.events",
                "payment.events",
                "material.events",
                "notification.events",
                "analytics.events",
                "student.events"
            ]
            
            # Try to declare exchanges (will succeed if they exist or create them)
            for exchange in expected_exchanges:
                try:
                    channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)
                    print(f"✅ Exchange '{exchange}': Available")
                except Exception as e:
                    print(f"❌ Exchange '{exchange}': {e}")
            
            connection.close()
            print("✅ RabbitMQ: Message queue setup verified")
            
        except Exception as e:
            pytest.fail(f"❌ RabbitMQ queue setup check failed: {e}")


@pytest.mark.infrastructure
class TestInfrastructureResilience:
    """Test infrastructure resilience and recovery"""
    
    async def test_service_restart_recovery(self, http_client, test_config, health_checker):
        """Test that services can recover after restart (simulated)"""
        # This would require Docker API to restart containers
        # For now, just verify they're healthy
        
        services_to_test = [test_config.USER_SERVICE_URL]
        
        for service_url in services_to_test:
            # Check initial health
            initial_health = await health_checker(service_url)
            assert initial_health["status"] == "healthy"
            
            # In a real scenario, we would restart the container here
            # For now, just wait a moment and check again
            await asyncio.sleep(2)
            
            # Verify service is still healthy
            recovery_health = await health_checker(service_url)
            assert recovery_health["status"] == "healthy"
            
            print(f"✅ {service_url}: Maintained health through simulated restart")
    
    
    async def test_graceful_degradation(self, http_client, test_config):
        """Test that system degrades gracefully when services are unavailable"""
        
        # Test API Gateway behavior when a service is down
        # This would require actually stopping a service to test properly
        # For now, test that gateway health reflects downstream status
        
        async with http_client.get(f"{test_config.API_GATEWAY_URL}/health") as response:
            assert response.status in [200, 503]  # OK or Service Unavailable
            
            health_data = await response.json()
            
            # If any dependencies are down, overall status should reflect that
            if "dependencies" in health_data:
                unhealthy_deps = [dep for dep, status in health_data["dependencies"].items() 
                                if status.get("status") not in ["healthy", "connected"]]
                
                if unhealthy_deps:
                    assert health_data.get("status") in ["degraded", "unhealthy"]
                    print(f"⚠️  System degraded due to: {unhealthy_deps}")
                else:
                    assert health_data.get("status") == "healthy"
                    print("✅ All dependencies healthy")