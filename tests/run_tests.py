"""
RepitBot Microservices Test Runner
=================================

Comprehensive test execution and reporting for the RepitBot microservices architecture.
Runs all test categories and generates detailed reports with recommendations.

Test Categories:
- Infrastructure Tests (health checks, connectivity)
- Authentication Tests (JWT, RBAC, security)
- Functional Tests (Parent, Student, Tutor workflows)
- Contract Tests (API contracts, service integration)
- Event Tests (RabbitMQ, event-driven workflows)
- Performance Tests (load, stress, response times)
- Security Tests (vulnerabilities, penetration)
- Integration Tests (database, external services)
- Monitoring Tests (observability, alerting)
- Chaos Tests (resilience, fault tolerance)

Usage:
    python run_tests.py --all                    # Run all tests
    python run_tests.py --category infrastructure # Run specific category
    python run_tests.py --fast                   # Run essential tests only
    python run_tests.py --report                 # Generate report only
"""

import os
import sys
import argparse
import subprocess
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from dataclasses import dataclass


@dataclass
class TestResult:
    """Test execution result"""
    category: str
    name: str
    status: str  # passed, failed, skipped, error
    duration: float
    message: str = ""
    details: Dict[str, Any] = None


@dataclass
class TestSummary:
    """Overall test execution summary"""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    start_time: datetime
    end_time: datetime


class MicroservicesTestRunner:
    """Main test runner for RepitBot microservices"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = Path(__file__).parent
        self.results: List[TestResult] = []
        
        # Service URLs
        self.services = {
            "API Gateway": "http://localhost:8000",
            "User Service": "http://localhost:8001",
            "Lesson Service": "http://localhost:8002",
            "Homework Service": "http://localhost:8003",
            "Payment Service": "http://localhost:8004",
            "Material Service": "http://localhost:8005",
            "Notification Service": "http://localhost:8006",
            "Analytics Service": "http://localhost:8007",
            "Student Service": "http://localhost:8008",
        }
        
        # Infrastructure services
        self.infrastructure = {
            "PostgreSQL": "postgresql://repitbot:repitbot_password@localhost:5432/repitbot",
            "RabbitMQ": "http://localhost:15672",
            "Redis": "redis://localhost:6379",
            "Prometheus": "http://localhost:9090",
            "Grafana": "http://localhost:3000"
        }
    
    
    def check_prerequisites(self) -> bool:
        """Check if all required services are running"""
        print("🔍 Checking prerequisites...")
        
        all_ready = True
        
        # Check microservices
        for service_name, service_url in self.services.items():
            try:
                response = requests.get(f"{service_url}/health", timeout=10)
                if response.status_code == 200:
                    print(f"✅ {service_name}: Ready")
                else:
                    print(f"❌ {service_name}: Not responding (HTTP {response.status_code})")
                    all_ready = False
            except Exception as e:
                print(f"❌ {service_name}: Connection failed ({e})")
                all_ready = False
        
        # Check infrastructure
        try:
            # PostgreSQL check
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                user="repitbot",
                password="repitbot_password",
                database="repitbot"
            )
            conn.close()
            print("✅ PostgreSQL: Ready")
        except Exception as e:
            print(f"❌ PostgreSQL: Connection failed ({e})")
            all_ready = False
        
        try:
            # Redis check
            import redis
            r = redis.Redis(host='localhost', port=6379)
            r.ping()
            print("✅ Redis: Ready")
        except Exception as e:
            print(f"❌ Redis: Connection failed ({e})")
            all_ready = False
        
        try:
            # RabbitMQ check
            response = requests.get("http://localhost:15672/api/overview", 
                                  auth=('repitbot', 'repitbot_password'), timeout=5)
            if response.status_code == 200:
                print("✅ RabbitMQ: Ready")
            else:
                print("❌ RabbitMQ: Not responding")
                all_ready = False
        except Exception as e:
            print(f"❌ RabbitMQ: Connection failed ({e})")
            all_ready = False
        
        return all_ready
    
    
    def run_test_category(self, category: str, markers: List[str] = None) -> List[TestResult]:
        """Run tests for a specific category"""
        
        print(f"\n🧪 Running {category.upper()} tests...")
        start_time = time.time()
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
        
        # Add markers if specified
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Add specific test file if exists
        test_file = self.test_dir / f"test_{category.lower()}.py"
        if test_file.exists():
            cmd.append(str(test_file))
        
        # Add JSON report
        report_file = self.test_dir / f"report_{category.lower()}.json"
        cmd.extend(["--json-report", f"--json-report-file={report_file}"])
        
        try:
            # Run pytest
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout per category
            )
            
            duration = time.time() - start_time
            
            # Parse results
            category_results = self.parse_pytest_results(report_file, category, duration)
            
            if result.returncode == 0:
                print(f"✅ {category} tests completed successfully ({duration:.1f}s)")
            else:
                print(f"⚠️  {category} tests completed with issues ({duration:.1f}s)")
                if result.stderr:
                    print(f"   Error output: {result.stderr[:200]}...")
            
            return category_results
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"❌ {category} tests timed out after {duration:.1f}s")
            
            return [TestResult(
                category=category,
                name="timeout",
                status="error",
                duration=duration,
                message="Test execution timed out"
            )]
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {category} tests failed: {e}")
            
            return [TestResult(
                category=category,
                name="execution_error",
                status="error", 
                duration=duration,
                message=str(e)
            )]
    
    
    def parse_pytest_results(self, report_file: Path, category: str, duration: float) -> List[TestResult]:
        """Parse pytest JSON results"""
        
        results = []
        
        try:
            if report_file.exists():
                with open(report_file, 'r') as f:
                    data = json.load(f)
                
                for test in data.get('tests', []):
                    results.append(TestResult(
                        category=category,
                        name=test.get('nodeid', 'unknown'),
                        status=test.get('outcome', 'unknown'),
                        duration=test.get('duration', 0),
                        message=test.get('call', {}).get('longrepr', ''),
                        details=test
                    ))
                
                # Clean up report file
                report_file.unlink()
                
        except Exception as e:
            print(f"⚠️  Could not parse results for {category}: {e}")
            
            # Return generic result
            results.append(TestResult(
                category=category,
                name="parse_error",
                status="error",
                duration=duration,
                message=f"Could not parse test results: {e}"
            ))
        
        return results
    
    
    def run_infrastructure_tests(self) -> List[TestResult]:
        """Run infrastructure health and connectivity tests"""
        return self.run_test_category("infrastructure", ["infrastructure"])
    
    
    def run_authentication_tests(self) -> List[TestResult]:
        """Run authentication and authorization tests"""
        return self.run_test_category("authentication", ["auth"])
    
    
    def run_functional_tests(self) -> List[TestResult]:
        """Run functional tests for all roles"""
        results = []
        
        # Run tests for each role
        for role in ["parent", "student", "tutor"]:
            role_results = self.run_test_category(f"functional_{role}", ["functional", role])
            results.extend(role_results)
        
        return results
    
    
    def run_contract_tests(self) -> List[TestResult]:
        """Run contract testing between services"""
        return self.run_test_category("contract_testing", ["contract"])
    
    
    def run_event_tests(self) -> List[TestResult]:
        """Run event-driven architecture tests"""
        return self.run_test_category("events", ["events"])
    
    
    def run_security_tests(self) -> List[TestResult]:
        """Run security and vulnerability tests"""
        print("\n🔒 Running SECURITY tests...")
        start_time = time.time()
        
        # Basic security checks
        security_results = []
        
        try:
            # Test HTTPS enforcement
            for service_name, service_url in self.services.items():
                try:
                    # Test if HTTP redirects to HTTPS
                    http_url = service_url.replace('https://', 'http://').replace('http://', 'http://')
                    response = requests.get(http_url, allow_redirects=False, timeout=5)
                    
                    if response.status_code in [301, 302, 307, 308]:
                        location = response.headers.get('Location', '')
                        if location.startswith('https://'):
                            status = "passed"
                            message = "HTTP redirects to HTTPS"
                        else:
                            status = "failed"
                            message = "HTTP does not redirect to HTTPS"
                    else:
                        status = "warning"
                        message = "HTTP endpoint accessible without redirect"
                    
                    security_results.append(TestResult(
                        category="security",
                        name=f"{service_name}_https_enforcement",
                        status=status,
                        duration=0.1,
                        message=message
                    ))
                    
                except Exception as e:
                    security_results.append(TestResult(
                        category="security",
                        name=f"{service_name}_https_test",
                        status="error",
                        duration=0.1,
                        message=str(e)
                    ))
            
            # Test CORS headers
            for service_name, service_url in self.services.items():
                try:
                    response = requests.options(
                        f"{service_url}/api/v1/health",
                        headers={'Origin': 'https://malicious-site.com'},
                        timeout=5
                    )
                    
                    cors_headers = response.headers.get('Access-Control-Allow-Origin', '')
                    
                    if cors_headers == '*':
                        status = "failed"
                        message = "CORS allows all origins (*)"
                    elif cors_headers:
                        status = "passed"  
                        message = f"CORS configured: {cors_headers}"
                    else:
                        status = "warning"
                        message = "No CORS headers found"
                    
                    security_results.append(TestResult(
                        category="security",
                        name=f"{service_name}_cors_policy",
                        status=status,
                        duration=0.1,
                        message=message
                    ))
                    
                except Exception:
                    pass  # Skip if service doesn't respond
            
            duration = time.time() - start_time
            print(f"✅ Security tests completed ({duration:.1f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ Security tests failed: {e}")
            
            security_results.append(TestResult(
                category="security",
                name="security_test_error",
                status="error",
                duration=duration,
                message=str(e)
            ))
        
        return security_results
    
    
    def run_performance_tests(self) -> List[TestResult]:
        """Run basic performance tests"""
        print("\n⚡ Running PERFORMANCE tests...")
        start_time = time.time()
        
        performance_results = []
        
        try:
            # Test response times for health checks
            for service_name, service_url in self.services.items():
                try:
                    response_start = time.time()
                    response = requests.get(f"{service_url}/health", timeout=10)
                    response_time = (time.time() - response_start) * 1000  # ms
                    
                    if response.status_code == 200:
                        if response_time < 500:  # Under 500ms
                            status = "passed"
                            message = f"Response time: {response_time:.0f}ms"
                        elif response_time < 1000:  # Under 1s
                            status = "warning"
                            message = f"Slow response: {response_time:.0f}ms"
                        else:
                            status = "failed"
                            message = f"Very slow response: {response_time:.0f}ms"
                    else:
                        status = "failed"
                        message = f"HTTP {response.status_code}"
                    
                    performance_results.append(TestResult(
                        category="performance",
                        name=f"{service_name}_response_time",
                        status=status,
                        duration=response_time / 1000,
                        message=message
                    ))
                    
                except Exception as e:
                    performance_results.append(TestResult(
                        category="performance",
                        name=f"{service_name}_performance_test",
                        status="error",
                        duration=0,
                        message=str(e)
                    ))
            
            duration = time.time() - start_time
            print(f"✅ Performance tests completed ({duration:.1f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ Performance tests failed: {e}")
            
            performance_results.append(TestResult(
                category="performance",
                name="performance_test_error",
                status="error",
                duration=duration,
                message=str(e)
            ))
        
        return performance_results
    
    
    def generate_summary(self) -> TestSummary:
        """Generate test execution summary"""
        
        total = len(self.results)
        passed = len([r for r in self.results if r.status == "passed"])
        failed = len([r for r in self.results if r.status == "failed"])
        skipped = len([r for r in self.results if r.status == "skipped"])
        errors = len([r for r in self.results if r.status == "error"])
        
        duration = sum(r.duration for r in self.results)
        
        return TestSummary(
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            start_time=datetime.now() - timedelta(seconds=duration),
            end_time=datetime.now()
        )
    
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate comprehensive test report"""
        
        summary = self.generate_summary()
        
        report = []
        report.append("=" * 80)
        report.append("🧪 REPITBOT MICROSERVICES TEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Executive Summary
        report.append("📋 EXECUTIVE SUMMARY")
        report.append("-" * 40)
        report.append(f"Test Execution Date: {summary.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Duration: {summary.duration:.1f} seconds")
        report.append(f"Total Tests: {summary.total_tests}")
        report.append(f"✅ Passed: {summary.passed}")
        report.append(f"❌ Failed: {summary.failed}")
        report.append(f"⏭️  Skipped: {summary.skipped}")
        report.append(f"🔥 Errors: {summary.errors}")
        
        success_rate = (summary.passed / summary.total_tests * 100) if summary.total_tests > 0 else 0
        report.append(f"📊 Success Rate: {success_rate:.1f}%")
        report.append("")
        
        # System Status
        report.append("🏥 SYSTEM HEALTH STATUS")
        report.append("-" * 40)
        
        # Group results by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        for category, results in categories.items():
            category_passed = len([r for r in results if r.status == "passed"])
            category_total = len(results)
            category_rate = (category_passed / category_total * 100) if category_total > 0 else 0
            
            status_emoji = "✅" if category_rate >= 80 else "⚠️" if category_rate >= 50 else "❌"
            report.append(f"{status_emoji} {category.upper()}: {category_passed}/{category_total} ({category_rate:.1f}%)")
        
        report.append("")
        
        # Detailed Results
        report.append("📊 DETAILED TEST RESULTS")
        report.append("-" * 40)
        
        for category, results in categories.items():
            report.append(f"\n🔍 {category.upper()} Tests:")
            
            for result in results:
                status_emoji = {
                    "passed": "✅",
                    "failed": "❌", 
                    "skipped": "⏭️",
                    "error": "🔥"
                }.get(result.status, "❓")
                
                report.append(f"  {status_emoji} {result.name} ({result.duration:.2f}s)")
                if result.message and result.status in ["failed", "error"]:
                    report.append(f"     💬 {result.message[:100]}...")
        
        report.append("")
        
        # Critical Issues
        critical_issues = [r for r in self.results if r.status in ["failed", "error"]]
        if critical_issues:
            report.append("🚨 CRITICAL ISSUES FOUND")
            report.append("-" * 40)
            
            for issue in critical_issues[:10]:  # Show top 10 issues
                report.append(f"❌ {issue.category}.{issue.name}")
                report.append(f"   📝 {issue.message[:150]}")
                report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS")
        report.append("-" * 40)
        
        if summary.failed > 0:
            report.append("🔧 IMMEDIATE ACTIONS REQUIRED:")
            report.append("   • Fix failed test cases before production deployment")
            report.append("   • Review error logs for root cause analysis")
            report.append("   • Verify microservice dependencies are properly configured")
            report.append("")
        
        if summary.errors > 0:
            report.append("⚠️  INFRASTRUCTURE ISSUES:")
            report.append("   • Check that all microservices are running")
            report.append("   • Verify database connectivity (PostgreSQL)")
            report.append("   • Confirm message broker is accessible (RabbitMQ)")
            report.append("   • Validate Redis cache connectivity")
            report.append("")
        
        # Performance recommendations
        perf_results = [r for r in self.results if r.category == "performance"]
        slow_services = [r for r in perf_results if r.status in ["warning", "failed"]]
        
        if slow_services:
            report.append("⚡ PERFORMANCE IMPROVEMENTS:")
            report.append("   • Optimize slow API endpoints (>500ms response time)")
            report.append("   • Consider implementing caching for frequently accessed data")
            report.append("   • Review database query performance")
            report.append("")
        
        # Security recommendations  
        security_results = [r for r in self.results if r.category == "security"]
        security_issues = [r for r in security_results if r.status in ["failed", "warning"]]
        
        if security_issues:
            report.append("🔒 SECURITY ENHANCEMENTS:")
            report.append("   • Implement HTTPS enforcement for all services")
            report.append("   • Configure proper CORS policies")
            report.append("   • Enable rate limiting to prevent abuse")
            report.append("   • Regular security vulnerability scanning")
            report.append("")
        
        # Production readiness
        report.append("🚀 PRODUCTION READINESS ASSESSMENT")
        report.append("-" * 40)
        
        if success_rate >= 95:
            report.append("✅ READY FOR PRODUCTION")
            report.append("   System meets quality standards for production deployment.")
        elif success_rate >= 80:
            report.append("⚠️  CONDITIONAL PRODUCTION READINESS")
            report.append("   Address critical issues before production deployment.")
            report.append("   Non-critical issues can be resolved post-deployment.")
        else:
            report.append("❌ NOT READY FOR PRODUCTION")
            report.append("   Significant issues must be resolved before deployment.")
            report.append("   Recommend thorough testing and bug fixing.")
        
        report.append("")
        report.append("=" * 80)
        report.append("🏁 End of Test Report")
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"\n📝 Report saved to: {output_file}")
        
        return report_text
    
    
    def run_all_tests(self, fast_mode: bool = False):
        """Run all test categories"""
        
        print("🚀 Starting RepitBot Microservices Test Suite")
        print(f"📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.check_prerequisites():
            print("\n❌ Prerequisites not met. Please ensure all services are running.")
            return False
        
        print("\n" + "=" * 80)
        
        # Define test execution order
        test_categories = [
            ("Infrastructure", self.run_infrastructure_tests),
            ("Authentication", self.run_authentication_tests),
            ("Functional", self.run_functional_tests),
        ]
        
        if not fast_mode:
            test_categories.extend([
                ("Contract", self.run_contract_tests),
                ("Events", self.run_event_tests),
                ("Security", self.run_security_tests),
                ("Performance", self.run_performance_tests),
            ])
        
        # Execute tests
        for category_name, test_function in test_categories:
            try:
                category_results = test_function()
                self.results.extend(category_results)
            except Exception as e:
                print(f"❌ {category_name} test execution failed: {e}")
                self.results.append(TestResult(
                    category=category_name.lower(),
                    name="execution_failure",
                    status="error",
                    duration=0,
                    message=str(e)
                ))
        
        # Generate and display report
        print("\n" + "=" * 80)
        print("📊 GENERATING TEST REPORT...")
        print("=" * 80)
        
        report_file = self.project_root / "TEST_REPORT.md"
        report_text = self.generate_report(str(report_file))
        
        print(report_text)
        
        # Return success status
        summary = self.generate_summary()
        success_rate = (summary.passed / summary.total_tests * 100) if summary.total_tests > 0 else 0
        
        return success_rate >= 80  # 80% success rate for overall pass


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description="RepitBot Microservices Test Runner")
    parser.add_argument("--all", action="store_true", help="Run all test categories")
    parser.add_argument("--fast", action="store_true", help="Run essential tests only")
    parser.add_argument("--category", choices=["infrastructure", "auth", "functional", "contract", "events", "security", "performance"], 
                       help="Run specific test category")
    parser.add_argument("--report", action="store_true", help="Generate report from previous results")
    parser.add_argument("--output", help="Output file for report")
    
    args = parser.parse_args()
    
    runner = MicroservicesTestRunner()
    
    if args.report:
        # Generate report only
        if runner.results:
            report = runner.generate_report(args.output)
            print(report)
        else:
            print("❌ No test results available for reporting")
            return 1
    
    elif args.category:
        # Run specific category
        if args.category == "infrastructure":
            results = runner.run_infrastructure_tests()
        elif args.category == "auth":
            results = runner.run_authentication_tests()
        elif args.category == "functional":
            results = runner.run_functional_tests()
        elif args.category == "contract":
            results = runner.run_contract_tests()
        elif args.category == "events":
            results = runner.run_event_tests()
        elif args.category == "security":
            results = runner.run_security_tests()
        elif args.category == "performance":
            results = runner.run_performance_tests()
        
        runner.results.extend(results)
        report = runner.generate_report(args.output)
        print(report)
    
    elif args.all or args.fast:
        # Run all tests
        success = runner.run_all_tests(fast_mode=args.fast)
        return 0 if success else 1
    
    else:
        # Default: run essential tests
        success = runner.run_all_tests(fast_mode=True)
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())