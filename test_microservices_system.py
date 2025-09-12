#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Microservices System Test
Полное тестирование микросервисной архитектуры RepitBot
"""
import asyncio
import httpx
import json
import time
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

class MicroservicesSystemTest:
    """Тестирование всей микросервисной системы"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results: List[Dict[str, Any]] = []
        
        # URLs сервисов
        self.services = {
            "api-gateway": "http://localhost:8000",
            "user-service": "http://localhost:8001", 
            "lesson-service": "http://localhost:8002",
            "homework-service": "http://localhost:8003",
            "payment-service": "http://localhost:8004",
            "material-service": "http://localhost:8005",
            "notification-service": "http://localhost:8006",
            "analytics-service": "http://localhost:8007",
            "student-service": "http://localhost:8008"
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_result(self, test_name: str, success: bool, message: str = "", duration: float = 0):
        """Логирование результата теста"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name:<40} {message}")
    
    async def test_service_health(self, service_name: str, url: str) -> bool:
        """Тестирование health endpoint сервиса"""
        start_time = time.time()
        
        try:
            response = await self.client.get(f"{url}/health")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    f"{service_name} Health Check",
                    True,
                    f"Status: {data.get('status', 'unknown')} ({duration:.2f}s)",
                    duration
                )
                return True
            else:
                self.log_result(
                    f"{service_name} Health Check",
                    False,
                    f"HTTP {response.status_code}",
                    duration
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_result(
                f"{service_name} Health Check",
                False,
                f"Connection error: {str(e)[:50]}",
                duration
            )
            return False
    
    async def test_api_gateway_routing(self) -> bool:
        """Тестирование маршрутизации API Gateway"""
        start_time = time.time()
        
        try:
            # Тест главной страницы Gateway
            response = await self.client.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                duration = time.time() - start_time
                
                # Проверяем, что есть информация о сервисах
                services_info = data.get("services", {})
                
                self.log_result(
                    "API Gateway Routing",
                    True,
                    f"Services: {len(services_info)} ({duration:.2f}s)",
                    duration
                )
                return True
            else:
                duration = time.time() - start_time
                self.log_result(
                    "API Gateway Routing",
                    False,
                    f"HTTP {response.status_code}",
                    duration
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_result(
                "API Gateway Routing",
                False,
                f"Error: {str(e)[:50]}",
                duration
            )
            return False
    
    async def test_student_service_integration(self) -> bool:
        """Тестирование Student Service интеграции"""
        start_time = time.time()
        
        try:
            # Тест получения достижений (без авторизации - должен вернуть ошибку или пустой результат)
            response = await self.client.get(f"{self.base_url}/api/v1/students/achievements")
            duration = time.time() - start_time
            
            # Ожидаем 401 (нет авторизации) или другой ожидаемый статус
            if response.status_code in [200, 401, 422]:
                self.log_result(
                    "Student Service Integration",
                    True,
                    f"API responds correctly ({duration:.2f}s)",
                    duration
                )
                return True
            else:
                self.log_result(
                    "Student Service Integration",
                    False,
                    f"Unexpected status: {response.status_code}",
                    duration
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_result(
                "Student Service Integration",
                False,
                f"Error: {str(e)[:50]}",
                duration
            )
            return False
    
    async def test_circuit_breaker_status(self) -> bool:
        """Тестирование состояния Circuit Breakers"""
        start_time = time.time()
        
        try:
            response = await self.client.get(f"{self.base_url}/gateway/metrics")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                circuit_breakers = data.get("circuit_breakers", {})
                
                self.log_result(
                    "Circuit Breaker Status",
                    True,
                    f"Monitoring {len(circuit_breakers)} breakers ({duration:.2f}s)",
                    duration
                )
                return True
            else:
                self.log_result(
                    "Circuit Breaker Status",
                    False,
                    f"HTTP {response.status_code}",
                    duration
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_result(
                "Circuit Breaker Status",
                False,
                f"Error: {str(e)[:50]}",
                duration
            )
            return False
    
    async def test_service_discovery(self) -> bool:
        """Тестирование Service Discovery"""
        start_time = time.time()
        
        try:
            response = await self.client.get(f"{self.base_url}/gateway/services")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                services = data.get("services", {})
                healthy = data.get("healthy", [])
                
                self.log_result(
                    "Service Discovery",
                    True,
                    f"Found {len(services)} services, {len(healthy)} healthy ({duration:.2f}s)",
                    duration
                )
                return True
            else:
                self.log_result(
                    "Service Discovery",
                    False,
                    f"HTTP {response.status_code}",
                    duration
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_result(
                "Service Discovery",
                False,
                f"Error: {str(e)[:50]}",
                duration
            )
            return False
    
    async def test_database_connections(self) -> bool:
        """Тестирование подключений к базам данных через health checks"""
        start_time = time.time()
        
        success_count = 0
        total_services = 0
        
        # Тестируем подробные health checks сервисов
        for service_name in ["user-service", "student-service", "lesson-service"]:
            if service_name in self.services:
                total_services += 1
                try:
                    url = self.services[service_name]
                    response = await self.client.get(f"{url}/health/detailed")
                    
                    if response.status_code == 200:
                        data = response.json()
                        checks = data.get("checks", {})
                        
                        if checks.get("database") == "healthy":
                            success_count += 1
                            
                except Exception:
                    pass  # Игнорируем ошибки, считаем неуспешным
        
        duration = time.time() - start_time
        success = success_count >= total_services // 2  # Минимум половина должна быть успешна
        
        self.log_result(
            "Database Connections",
            success,
            f"{success_count}/{total_services} services connected ({duration:.2f}s)",
            duration
        )
        
        return success
    
    async def test_event_bus_connectivity(self) -> bool:
        """Тестирование подключения к Event Bus (RabbitMQ)"""
        start_time = time.time()
        
        try:
            # Проверяем RabbitMQ Management API
            response = await self.client.get(
                "http://localhost:15672/api/overview",
                auth=("repitbot", "repitbot_password")
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                exchanges = data.get("object_totals", {}).get("exchanges", 0)
                queues = data.get("object_totals", {}).get("queues", 0)
                
                self.log_result(
                    "Event Bus Connectivity",
                    True,
                    f"RabbitMQ: {exchanges} exchanges, {queues} queues ({duration:.2f}s)",
                    duration
                )
                return True
            else:
                self.log_result(
                    "Event Bus Connectivity",
                    False,
                    f"RabbitMQ Management HTTP {response.status_code}",
                    duration
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_result(
                "Event Bus Connectivity",
                False,
                f"RabbitMQ connection error: {str(e)[:50]}",
                duration
            )
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Запуск всех тестов"""
        print("🚀 Starting Microservices System Test Suite")
        print("=" * 80)
        
        total_start_time = time.time()
        
        # 1. Health checks всех сервисов
        print("\n📋 1. Service Health Checks")
        print("-" * 40)
        health_results = []
        for service_name, url in self.services.items():
            result = await self.test_service_health(service_name, url)
            health_results.append(result)
        
        # 2. API Gateway функциональность
        print("\n🌐 2. API Gateway Tests")
        print("-" * 40)
        await self.test_api_gateway_routing()
        await self.test_circuit_breaker_status()
        await self.test_service_discovery()
        
        # 3. Интеграционные тесты
        print("\n🔗 3. Integration Tests")
        print("-" * 40)
        await self.test_student_service_integration()
        await self.test_database_connections()
        await self.test_event_bus_connectivity()
        
        total_duration = time.time() - total_start_time
        
        # Подсчет результатов
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Финальный отчет
        print("\n" + "=" * 80)
        print("📊 FINAL RESULTS")
        print("=" * 80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Статус системы
        if success_rate >= 80:
            system_status = "🟢 SYSTEM HEALTHY"
        elif success_rate >= 60:
            system_status = "🟡 SYSTEM DEGRADED"
        else:
            system_status = "🔴 SYSTEM UNHEALTHY"
        
        print(f"\nSystem Status: {system_status}")
        
        # Детальные результаты для неуспешных тестов
        failed_results = [r for r in self.test_results if not r["success"]]
        if failed_results:
            print("\n❌ Failed Tests Details:")
            for result in failed_results:
                print(f"  - {result['test']}: {result['message']}")
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": success_rate,
            "duration": total_duration,
            "system_healthy": success_rate >= 80,
            "results": self.test_results
        }

async def main():
    """Главная функция"""
    try:
        async with MicroservicesSystemTest() as test_suite:
            results = await test_suite.run_all_tests()
            
            # Сохранение результатов
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"test_results_{timestamp}.json"
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"\n📄 Test results saved to: {results_file}")
            
            # Возврат соответствующего exit кода
            if results["system_healthy"]:
                print("\n🎉 All systems operational!")
                sys.exit(0)
            else:
                print("\n⚠️  Some issues detected. Check the logs.")
                sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())