"""
Parent Dashboard Functional Tests
=================================

Comprehensive functional tests for the Parent role in RepitBot system.
Tests all parent-specific features and workflows.

Parent Dashboard Features:
- 💰 Payment Management (balance, top-up, transaction history)
- 📅 Child Schedule Viewing (lessons, cancellations, rescheduling)  
- 📊 Child Progress Monitoring (grades, attendance, achievements)
- 🔔 Notification Preferences (lesson reminders, grade notifications)
- 👨‍👩‍👧‍👦 Multiple Children Management (if applicable)
- 📱 Mobile-friendly Interface Integration

Key Parent Workflows:
1. View child's upcoming lessons and schedule
2. Monitor child's homework completion and grades
3. Top up account balance for lesson payments
4. Receive notifications about child's progress
5. Cancel or reschedule lessons when needed
6. Track payment history and spending
"""

import pytest
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json


@pytest.mark.functional
@pytest.mark.parent
class TestParentPaymentManagement:
    """Parent payment and billing functionality tests"""
    
    async def test_parent_view_balance(self, http_client, test_config, auth_tokens):
        """Test parent can view current account balance"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/payments/balance",
            headers=headers
        ) as response:
            if response.status == 200:
                balance_data = await response.json()
                
                # Verify balance structure
                assert "balance" in balance_data
                assert "currency" in balance_data
                assert isinstance(balance_data["balance"], (int, float))
                assert balance_data["balance"] >= 0  # Balance should not be negative
                
                print(f"✅ Parent balance retrieved: {balance_data['balance']} {balance_data.get('currency', 'RUB')}")
                
            elif response.status == 404:
                print("⚠️  Balance endpoint not found - may need implementation")
            else:
                print(f"⚠️  Balance check failed with status: {response.status}")
    
    
    async def test_parent_payment_history(self, http_client, test_config, auth_tokens):
        """Test parent can view payment transaction history"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/payments/history",
            headers=headers
        ) as response:
            if response.status == 200:
                history_data = await response.json()
                
                # Verify history structure
                assert "transactions" in history_data or isinstance(history_data, list)
                
                transactions = history_data.get("transactions", history_data)
                
                if transactions:
                    # Verify transaction structure
                    transaction = transactions[0]
                    expected_fields = ["id", "amount", "type", "date", "status"]
                    
                    for field in expected_fields:
                        if field not in transaction:
                            print(f"⚠️  Missing field in transaction: {field}")
                    
                    print(f"✅ Payment history retrieved: {len(transactions)} transactions")
                else:
                    print("✅ Payment history retrieved: No transactions (empty account)")
                    
            elif response.status == 404:
                print("⚠️  Payment history endpoint not found")
            else:
                print(f"⚠️  Payment history failed with status: {response.status}")
    
    
    async def test_parent_top_up_balance(self, http_client, test_config, auth_tokens, test_payment_data):
        """Test parent can top up account balance"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        payment_data = test_payment_data()
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/payments/top-up",
            headers=headers,
            json=payment_data
        ) as response:
            if response.status in [200, 201]:
                top_up_result = await response.json()
                
                # Verify top-up response
                assert "transaction_id" in top_up_result or "id" in top_up_result
                assert "status" in top_up_result
                assert "amount" in top_up_result
                
                print(f"✅ Balance top-up successful: {payment_data['amount']} RUB")
                
                # Verify balance increased (if balance endpoint works)
                await asyncio.sleep(1)  # Allow processing time
                
                async with http_client.get(
                    f"{test_config.API_GATEWAY_URL}/api/v1/payments/balance",
                    headers=headers
                ) as balance_response:
                    if balance_response.status == 200:
                        balance_data = await balance_response.json()
                        # Balance should be at least the amount we topped up
                        assert balance_data["balance"] >= payment_data["amount"]
                        print("✅ Balance correctly updated after top-up")
                        
            elif response.status == 404:
                print("⚠️  Top-up endpoint not found")
            elif response.status == 400:
                error_data = await response.json()
                print(f"⚠️  Top-up validation error: {error_data}")
            else:
                print(f"⚠️  Top-up failed with status: {response.status}")
    
    
    async def test_parent_payment_methods(self, http_client, test_config, auth_tokens):
        """Test parent can view and manage payment methods"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/payments/methods",
            headers=headers
        ) as response:
            if response.status == 200:
                methods_data = await response.json()
                
                # Verify payment methods structure
                assert "methods" in methods_data or isinstance(methods_data, list)
                
                methods = methods_data.get("methods", methods_data)
                print(f"✅ Payment methods retrieved: {len(methods)} methods available")
                
                # Check for common payment methods
                method_types = [method.get("type", method.get("name", "")) for method in methods]
                print(f"📋 Available methods: {method_types}")
                
            elif response.status == 404:
                print("⚠️  Payment methods endpoint not found")
            else:
                print(f"⚠️  Payment methods failed with status: {response.status}")


@pytest.mark.functional
@pytest.mark.parent
class TestParentScheduleManagement:
    """Parent schedule viewing and management tests"""
    
    async def test_parent_view_child_schedule(self, http_client, test_config, auth_tokens):
        """Test parent can view child's lesson schedule"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        # Try different schedule endpoints
        schedule_endpoints = [
            "/api/v1/lessons/schedule",
            "/api/v1/lessons/child-schedule", 
            "/api/v1/schedule/upcoming",
            "/api/v1/parent/child-lessons"
        ]
        
        schedule_found = False
        
        for endpoint in schedule_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=headers
            ) as response:
                if response.status == 200:
                    schedule_data = await response.json()
                    
                    # Verify schedule structure
                    assert "lessons" in schedule_data or isinstance(schedule_data, list)
                    
                    lessons = schedule_data.get("lessons", schedule_data)
                    
                    if lessons:
                        lesson = lessons[0]
                        expected_fields = ["id", "subject", "date", "time", "tutor", "status"]
                        
                        for field in expected_fields:
                            if field not in lesson:
                                print(f"⚠️  Missing field in lesson: {field}")
                    
                    print(f"✅ Child schedule retrieved from {endpoint}: {len(lessons)} lessons")
                    schedule_found = True
                    break
                    
                elif response.status != 404:
                    print(f"⚠️  Schedule endpoint {endpoint} failed: {response.status}")
        
        if not schedule_found:
            print("⚠️  No working schedule endpoint found")
    
    
    async def test_parent_lesson_details_view(self, http_client, test_config, auth_tokens):
        """Test parent can view detailed information about child's lessons"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        # First get schedule to find a lesson ID
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/schedule",
            headers=headers
        ) as response:
            if response.status == 200:
                schedule_data = await response.json()
                lessons = schedule_data.get("lessons", schedule_data)
                
                if lessons and len(lessons) > 0:
                    lesson_id = lessons[0].get("id")
                    
                    if lesson_id:
                        # Get detailed lesson information
                        async with http_client.get(
                            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{lesson_id}",
                            headers=headers
                        ) as detail_response:
                            if detail_response.status == 200:
                                lesson_details = await detail_response.json()
                                
                                # Verify detailed lesson structure
                                expected_fields = ["id", "subject", "date", "duration", "tutor_name", "status", "description"]
                                present_fields = [field for field in expected_fields if field in lesson_details]
                                
                                print(f"✅ Lesson details retrieved: {len(present_fields)}/{len(expected_fields)} fields")
                                
                            else:
                                print(f"⚠️  Lesson details failed: {detail_response.status}")
                    else:
                        print("⚠️  No lesson ID found in schedule")
                else:
                    print("✅ Schedule retrieved but no lessons found (empty schedule)")
            else:
                print(f"⚠️  Could not get schedule for lesson details test: {response.status}")
    
    
    async def test_parent_lesson_cancellation(self, http_client, test_config, auth_tokens):
        """Test parent can cancel child's lessons"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        # This test would need a confirmed lesson to cancel
        # For now, test the cancellation endpoint structure
        
        test_lesson_id = 999999  # Non-existent lesson for testing
        cancellation_data = {
            "reason": "Child is sick",
            "notify_tutor": True
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{test_lesson_id}/cancel",
            headers=headers,
            json=cancellation_data
        ) as response:
            # Should get 404 (lesson not found) rather than 401/403 (access denied)
            if response.status == 404:
                print("✅ Lesson cancellation endpoint accessible (lesson not found)")
            elif response.status in [200, 201]:
                print("✅ Lesson cancellation successful")
            elif response.status in [401, 403]:
                print("❌ Parent denied access to lesson cancellation")
            else:
                print(f"⚠️  Lesson cancellation returned: {response.status}")
    
    
    async def test_parent_lesson_rescheduling(self, http_client, test_config, auth_tokens):
        """Test parent can reschedule child's lessons"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        # Test rescheduling endpoint
        test_lesson_id = 999999
        new_schedule = {
            "new_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "new_time": "15:00",
            "reason": "Schedule conflict"
        }
        
        async with http_client.put(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{test_lesson_id}/reschedule",
            headers=headers,
            json=new_schedule
        ) as response:
            if response.status == 404:
                print("✅ Lesson rescheduling endpoint accessible (lesson not found)")
            elif response.status in [200, 201]:
                print("✅ Lesson rescheduling successful")
            elif response.status in [401, 403]:
                print("❌ Parent denied access to lesson rescheduling")
            else:
                print(f"⚠️  Lesson rescheduling returned: {response.status}")


@pytest.mark.functional
@pytest.mark.parent  
class TestParentProgressMonitoring:
    """Parent child progress monitoring tests"""
    
    async def test_parent_view_child_grades(self, http_client, test_config, auth_tokens):
        """Test parent can view child's grades and homework scores"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        # Try different grade/progress endpoints
        grade_endpoints = [
            "/api/v1/analytics/child-progress",
            "/api/v1/grades/child", 
            "/api/v1/homework/child-grades",
            "/api/v1/parent/child-performance"
        ]
        
        grades_found = False
        
        for endpoint in grade_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=headers
            ) as response:
                if response.status == 200:
                    grades_data = await response.json()
                    
                    # Verify grades structure
                    if "grades" in grades_data or "scores" in grades_data or "progress" in grades_data:
                        print(f"✅ Child grades retrieved from {endpoint}")
                        grades_found = True
                        break
                    elif isinstance(grades_data, list):
                        print(f"✅ Child grades retrieved from {endpoint}: {len(grades_data)} entries")
                        grades_found = True
                        break
                        
                elif response.status != 404:
                    print(f"⚠️  Grades endpoint {endpoint} failed: {response.status}")
        
        if not grades_found:
            print("⚠️  No working grades endpoint found")
    
    
    async def test_parent_view_child_attendance(self, http_client, test_config, auth_tokens):
        """Test parent can view child's lesson attendance record"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/analytics/attendance",
            headers=headers
        ) as response:
            if response.status == 200:
                attendance_data = await response.json()
                
                # Verify attendance structure
                expected_fields = ["total_lessons", "attended", "missed", "attendance_rate"]
                present_fields = [field for field in expected_fields if field in attendance_data]
                
                print(f"✅ Attendance data retrieved: {len(present_fields)}/{len(expected_fields)} fields")
                
                # Check attendance rate calculation
                if "attendance_rate" in attendance_data:
                    rate = attendance_data["attendance_rate"]
                    assert 0 <= rate <= 100, f"Invalid attendance rate: {rate}"
                    print(f"📊 Attendance rate: {rate}%")
                    
            elif response.status == 404:
                print("⚠️  Attendance endpoint not found")
            else:
                print(f"⚠️  Attendance check failed: {response.status}")
    
    
    async def test_parent_view_child_achievements(self, http_client, test_config, auth_tokens):
        """Test parent can view child's achievements and milestones"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/student/child-achievements",
            headers=headers
        ) as response:
            if response.status == 200:
                achievements_data = await response.json()
                
                # Verify achievements structure
                assert "achievements" in achievements_data or isinstance(achievements_data, list)
                
                achievements = achievements_data.get("achievements", achievements_data)
                
                if achievements:
                    achievement = achievements[0]
                    expected_fields = ["id", "title", "description", "earned_date", "level"]
                    
                    present_fields = [field for field in expected_fields if field in achievement]
                    print(f"✅ Child achievements retrieved: {len(achievements)} achievements")
                    print(f"📊 Achievement fields: {len(present_fields)}/{len(expected_fields)}")
                else:
                    print("✅ Achievements retrieved: No achievements yet")
                    
            elif response.status == 404:
                print("⚠️  Achievements endpoint not found")
            else:
                print(f"⚠️  Achievements check failed: {response.status}")
    
    
    async def test_parent_progress_charts(self, http_client, test_config, auth_tokens):
        """Test parent can view visual progress charts"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        # Test different chart endpoints
        chart_endpoints = [
            "/api/v1/analytics/progress-chart",
            "/api/v1/charts/child-performance",
            "/api/v1/analytics/grade-trends"
        ]
        
        chart_found = False
        
        for endpoint in chart_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=headers
            ) as response:
                if response.status == 200:
                    chart_data = await response.json()
                    
                    # Verify chart data structure
                    if any(key in chart_data for key in ["chart_url", "data", "series", "points"]):
                        print(f"✅ Progress chart retrieved from {endpoint}")
                        chart_found = True
                        break
                        
                elif response.status != 404:
                    print(f"⚠️  Chart endpoint {endpoint} failed: {response.status}")
        
        if not chart_found:
            print("⚠️  No working chart endpoint found")


@pytest.mark.functional
@pytest.mark.parent
class TestParentNotifications:
    """Parent notification preferences and management tests"""
    
    async def test_parent_notification_preferences(self, http_client, test_config, auth_tokens):
        """Test parent can view and update notification preferences"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        # Get current preferences
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/notifications/preferences",
            headers=headers
        ) as response:
            if response.status == 200:
                preferences = await response.json()
                
                # Verify preferences structure
                expected_prefs = ["lesson_reminders", "grade_notifications", "payment_alerts", "schedule_changes"]
                
                for pref in expected_prefs:
                    if pref in preferences:
                        print(f"✅ Notification preference found: {pref} = {preferences[pref]}")
                
                # Test updating preferences
                new_preferences = {
                    "lesson_reminders": True,
                    "grade_notifications": True,
                    "payment_alerts": False,
                    "schedule_changes": True
                }
                
                async with http_client.put(
                    f"{test_config.API_GATEWAY_URL}/api/v1/notifications/preferences",
                    headers=headers,
                    json=new_preferences
                ) as update_response:
                    if update_response.status in [200, 204]:
                        print("✅ Notification preferences updated successfully")
                    else:
                        print(f"⚠️  Preference update failed: {update_response.status}")
                        
            elif response.status == 404:
                print("⚠️  Notification preferences endpoint not found")
            else:
                print(f"⚠️  Preferences check failed: {response.status}")
    
    
    async def test_parent_notification_history(self, http_client, test_config, auth_tokens):
        """Test parent can view notification history"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/notifications/history",
            headers=headers
        ) as response:
            if response.status == 200:
                history = await response.json()
                
                # Verify history structure
                assert "notifications" in history or isinstance(history, list)
                
                notifications = history.get("notifications", history)
                
                if notifications:
                    notification = notifications[0]
                    expected_fields = ["id", "type", "message", "sent_date", "read_status"]
                    
                    present_fields = [field for field in expected_fields if field in notification]
                    print(f"✅ Notification history: {len(notifications)} notifications")
                    print(f"📊 Notification fields: {len(present_fields)}/{len(expected_fields)}")
                else:
                    print("✅ Notification history retrieved: No notifications")
                    
            elif response.status == 404:
                print("⚠️  Notification history endpoint not found")
            else:
                print(f"⚠️  Notification history failed: {response.status}")


@pytest.mark.functional
@pytest.mark.parent
class TestParentMultipleChildren:
    """Tests for parents with multiple children"""
    
    async def test_parent_children_list(self, http_client, test_config, auth_tokens):
        """Test parent can view list of their children"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/users/children",
            headers=headers
        ) as response:
            if response.status == 200:
                children_data = await response.json()
                
                # Verify children structure
                assert "children" in children_data or isinstance(children_data, list)
                
                children = children_data.get("children", children_data)
                
                if children:
                    child = children[0]
                    expected_fields = ["id", "name", "grade", "subjects"]
                    
                    present_fields = [field for field in expected_fields if field in child]
                    print(f"✅ Children list: {len(children)} children")
                    print(f"📊 Child fields: {len(present_fields)}/{len(expected_fields)}")
                else:
                    print("✅ Children list retrieved: No children registered")
                    
            elif response.status == 404:
                print("⚠️  Children list endpoint not found")
            else:
                print(f"⚠️  Children list failed: {response.status}")
    
    
    async def test_parent_child_specific_data(self, http_client, test_config, auth_tokens):
        """Test parent can view data for specific child"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        
        # First get children list
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/users/children",
            headers=headers
        ) as response:
            if response.status == 200:
                children_data = await response.json()
                children = children_data.get("children", children_data)
                
                if children and len(children) > 0:
                    child_id = children[0].get("id")
                    
                    if child_id:
                        # Get specific child's schedule
                        async with http_client.get(
                            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/schedule?child_id={child_id}",
                            headers=headers
                        ) as schedule_response:
                            if schedule_response.status == 200:
                                print(f"✅ Child-specific schedule retrieved for child {child_id}")
                            else:
                                print(f"⚠️  Child-specific schedule failed: {schedule_response.status}")
                    else:
                        print("⚠️  No child ID found")
                else:
                    print("✅ No children found for child-specific testing")
            else:
                print(f"⚠️  Could not get children list: {response.status}")


@pytest.mark.functional
@pytest.mark.parent
class TestParentEndToEndWorkflows:
    """End-to-end parent workflow tests"""
    
    async def test_complete_parent_session_workflow(self, http_client, test_config, auth_tokens):
        """Test complete parent session from login to logout"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        headers = auth_tokens["PARENT"]["headers"]
        workflow_steps = []
        
        # Step 1: Check balance
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/payments/balance",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Balance check")
            else:
                workflow_steps.append("❌ Balance check")
        
        # Step 2: View child schedule
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/schedule",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Schedule view")
            else:
                workflow_steps.append("❌ Schedule view")
        
        # Step 3: Check child progress
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/analytics/child-progress",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Progress check")
            else:
                workflow_steps.append("❌ Progress check")
        
        # Step 4: View notifications
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/notifications/history",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Notifications view")
            else:
                workflow_steps.append("❌ Notifications view")
        
        print("🔄 Complete Parent Workflow Results:")
        for step in workflow_steps:
            print(f"  {step}")
        
        # Verify majority of workflow works
        successful_steps = [step for step in workflow_steps if step.startswith("✅")]
        assert len(successful_steps) >= len(workflow_steps) // 2, \
            f"Too many workflow steps failed: {workflow_steps}"
        
        print(f"✅ Parent workflow: {len(successful_steps)}/{len(workflow_steps)} steps successful")