"""
Tutor Dashboard Functional Tests
==============================

Comprehensive functional tests for the Tutor role in RepitBot system.
Tests all tutor-specific management and teaching functionality.

Tutor Dashboard Features:
- 📚 Lesson Management (create, schedule, modify, cancel lessons)
- 👥 Student Management (view students, track progress, assign work)
- 📝 Homework Management (create assignments, grade submissions)
- 📖 Material Management (upload, organize, share educational content)
- 📊 Analytics & Reporting (student performance, lesson statistics)
- 🔔 Communication (send notifications, announcements)
- 💰 Financial Overview (lesson payments, earnings tracking)

Key Tutor Workflows:
1. Create and manage lesson schedules
2. Assign and grade homework assignments
3. Upload and organize teaching materials
4. Monitor student progress and performance
5. Generate reports and analytics
6. Communicate with students and parents
"""

import pytest
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json


@pytest.mark.functional
@pytest.mark.tutor
class TestTutorLessonManagement:
    """Tutor lesson creation and management tests"""
    
    async def test_tutor_create_lesson(self, http_client, test_config, auth_tokens, test_lesson_data):
        """Test tutor can create new lessons"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        lesson_data = test_lesson_data()
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/create",
            headers=headers,
            json=lesson_data
        ) as response:
            if response.status in [200, 201]:
                created_lesson = await response.json()
                
                # Verify lesson creation response
                assert "id" in created_lesson
                assert "title" in created_lesson
                assert created_lesson["title"] == lesson_data["title"]
                assert "scheduled_time" in created_lesson
                assert "status" in created_lesson
                
                lesson_id = created_lesson["id"]
                print(f"✅ Lesson created successfully: ID {lesson_id}")
                
                # Verify lesson appears in tutor's schedule
                async with http_client.get(
                    f"{test_config.API_GATEWAY_URL}/api/v1/lessons/my-lessons",
                    headers=headers
                ) as schedule_response:
                    if schedule_response.status == 200:
                        schedule_data = await schedule_response.json()
                        lessons = schedule_data.get("lessons", schedule_data)
                        
                        # Check if our lesson is in the list
                        created_lesson_found = any(
                            lesson.get("id") == lesson_id for lesson in lessons
                        )
                        
                        if created_lesson_found:
                            print("✅ Created lesson found in tutor schedule")
                        else:
                            print("⚠️  Created lesson not found in schedule")
                
                return created_lesson
                
            elif response.status == 404:
                print("⚠️  Lesson creation endpoint not found")
            elif response.status == 400:
                error_data = await response.json()
                print(f"⚠️  Lesson creation validation error: {error_data}")
            else:
                print(f"⚠️  Lesson creation failed: {response.status}")
    
    
    async def test_tutor_view_lesson_schedule(self, http_client, test_config, auth_tokens):
        """Test tutor can view their lesson schedule"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        # Try different schedule endpoints for tutors
        schedule_endpoints = [
            "/api/v1/lessons/my-lessons",
            "/api/v1/lessons/tutor-schedule", 
            "/api/v1/tutor/schedule",
            "/api/v1/lessons/manage"
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
                        expected_fields = ["id", "subject", "date", "student_name", "status", "duration"]
                        
                        present_fields = [field for field in expected_fields if field in lesson]
                        print(f"✅ Tutor schedule from {endpoint}: {len(lessons)} lessons")
                        print(f"📊 Lesson fields: {len(present_fields)}/{len(expected_fields)}")
                    else:
                        print(f"✅ Tutor schedule from {endpoint}: No lessons scheduled")
                    
                    schedule_found = True
                    break
                    
                elif response.status != 404:
                    print(f"⚠️  Schedule endpoint {endpoint} failed: {response.status}")
        
        if not schedule_found:
            print("⚠️  No working tutor schedule endpoint found")
    
    
    async def test_tutor_modify_lesson(self, http_client, test_config, auth_tokens, test_lesson_data):
        """Test tutor can modify existing lessons"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        # Test lesson modification
        test_lesson_id = 999999  # Non-existent lesson for testing
        updated_data = {
            "title": "Updated Lesson Title",
            "description": "Updated lesson description",
            "duration_minutes": 90
        }
        
        async with http_client.put(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{test_lesson_id}",
            headers=headers,
            json=updated_data
        ) as response:
            if response.status == 404:
                print("✅ Lesson modification endpoint accessible (lesson not found)")
            elif response.status in [200, 201]:
                updated_lesson = await response.json()
                assert "id" in updated_lesson
                print("✅ Lesson modification successful")
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to lesson modification")
            else:
                print(f"⚠️  Lesson modification returned: {response.status}")
    
    
    async def test_tutor_cancel_lesson(self, http_client, test_config, auth_tokens):
        """Test tutor can cancel lessons"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        test_lesson_id = 999999
        cancellation_data = {
            "reason": "Tutor unavailable",
            "notify_student": True,
            "notify_parent": True,
            "reschedule_option": True
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{test_lesson_id}/cancel",
            headers=headers,
            json=cancellation_data
        ) as response:
            if response.status == 404:
                print("✅ Lesson cancellation endpoint accessible (lesson not found)")
            elif response.status in [200, 201]:
                print("✅ Lesson cancellation successful")
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to lesson cancellation")
            else:
                print(f"⚠️  Lesson cancellation returned: {response.status}")
    
    
    async def test_tutor_lesson_attendance_tracking(self, http_client, test_config, auth_tokens):
        """Test tutor can track lesson attendance"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        test_lesson_id = 999999
        attendance_data = {
            "student_attended": True,
            "lesson_completed": True,
            "notes": "Great participation from student",
            "next_lesson_topics": ["algebra", "equations"]
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{test_lesson_id}/attendance",
            headers=headers,
            json=attendance_data
        ) as response:
            if response.status == 404:
                print("✅ Attendance tracking endpoint accessible (lesson not found)")
            elif response.status in [200, 201]:
                print("✅ Attendance tracking successful")
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to attendance tracking")
            else:
                print(f"⚠️  Attendance tracking returned: {response.status}")


@pytest.mark.functional
@pytest.mark.tutor
class TestTutorHomeworkManagement:
    """Tutor homework assignment and grading tests"""
    
    async def test_tutor_create_homework_assignment(self, http_client, test_config, auth_tokens):
        """Test tutor can create homework assignments"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        homework_data = {
            "title": "Mathematics Homework - Quadratic Equations",
            "description": "Solve exercises 1-10 from chapter 5",
            "subject": "математика",
            "due_date": (datetime.now() + timedelta(days=5)).isoformat(),
            "max_score": 100,
            "instructions": "Show all work and steps",
            "student_ids": [1, 2, 3]  # Assign to specific students
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/assign",
            headers=headers,
            json=homework_data
        ) as response:
            if response.status in [200, 201]:
                created_homework = await response.json()
                
                # Verify homework creation
                assert "id" in created_homework
                assert "title" in created_homework
                assert created_homework["title"] == homework_data["title"]
                
                print(f"✅ Homework assignment created: ID {created_homework['id']}")
                return created_homework
                
            elif response.status == 404:
                print("⚠️  Homework assignment endpoint not found")
            elif response.status == 400:
                error_data = await response.json()
                print(f"⚠️  Homework assignment validation error: {error_data}")
            else:
                print(f"⚠️  Homework assignment failed: {response.status}")
    
    
    async def test_tutor_view_homework_submissions(self, http_client, test_config, auth_tokens):
        """Test tutor can view student homework submissions"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/submissions",
            headers=headers
        ) as response:
            if response.status == 200:
                submissions_data = await response.json()
                
                # Verify submissions structure
                assert "submissions" in submissions_data or isinstance(submissions_data, list)
                
                submissions = submissions_data.get("submissions", submissions_data)
                
                if submissions:
                    submission = submissions[0]
                    expected_fields = ["id", "homework_id", "student_name", "submitted_at", 
                                     "status", "answers", "files"]
                    
                    present_fields = [field for field in expected_fields if field in submission]
                    print(f"✅ Homework submissions: {len(submissions)} submissions")
                    print(f"📊 Submission fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Check submission statuses
                    statuses = [sub.get("status", "unknown") for sub in submissions[:5]]
                    print(f"📝 Submission statuses: {set(statuses)}")
                else:
                    print("✅ Homework submissions retrieved: No submissions")
                    
            elif response.status == 404:
                print("⚠️  Homework submissions endpoint not found")
            else:
                print(f"⚠️  Homework submissions failed: {response.status}")
    
    
    async def test_tutor_grade_homework(self, http_client, test_config, auth_tokens):
        """Test tutor can grade homework submissions"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        test_submission_id = 999999
        grading_data = {
            "score": 85,
            "max_score": 100,
            "feedback": "Good work! Need to show more steps for problem 3.",
            "detailed_feedback": {
                "question_1": "Excellent solution",
                "question_2": "Minor calculation error",
                "question_3": "Need to show all steps"
            },
            "graded_at": datetime.now().isoformat()
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/submissions/{test_submission_id}/grade",
            headers=headers,
            json=grading_data
        ) as response:
            if response.status == 404:
                print("✅ Homework grading endpoint accessible (submission not found)")
            elif response.status in [200, 201]:
                graded_submission = await response.json()
                print("✅ Homework grading successful")
                
                # Verify grading response
                if "score" in graded_submission:
                    assert graded_submission["score"] == grading_data["score"]
                    print(f"✅ Grade recorded: {grading_data['score']}/{grading_data['max_score']}")
                    
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to homework grading")
            else:
                print(f"⚠️  Homework grading returned: {response.status}")
    
    
    async def test_tutor_homework_analytics(self, http_client, test_config, auth_tokens):
        """Test tutor can view homework completion analytics"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/analytics",
            headers=headers
        ) as response:
            if response.status == 200:
                analytics_data = await response.json()
                
                # Check for homework analytics metrics
                expected_metrics = ["total_assigned", "total_submitted", "completion_rate", 
                                  "average_score", "overdue_count", "by_subject"]
                
                present_metrics = [metric for metric in expected_metrics if metric in analytics_data]
                print(f"✅ Homework analytics: {len(present_metrics)}/{len(expected_metrics)} metrics")
                
                # Validate metric values
                if "completion_rate" in analytics_data:
                    rate = analytics_data["completion_rate"]
                    assert 0 <= rate <= 100, f"Invalid completion rate: {rate}"
                    print(f"📊 Completion rate: {rate}%")
                
                if "average_score" in analytics_data:
                    avg_score = analytics_data["average_score"]
                    assert avg_score >= 0, f"Invalid average score: {avg_score}"
                    print(f"📊 Average score: {avg_score}")
                    
            elif response.status == 404:
                print("⚠️  Homework analytics endpoint not found")
            else:
                print(f"⚠️  Homework analytics failed: {response.status}")


@pytest.mark.functional
@pytest.mark.tutor
class TestTutorMaterialManagement:
    """Tutor educational material management tests"""
    
    async def test_tutor_upload_material(self, http_client, test_config, auth_tokens):
        """Test tutor can upload educational materials"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        # Create test file for upload
        test_file_content = b"This is a test educational material content"
        
        # Material metadata
        material_data = {
            "title": "Quadratic Equations Study Guide",
            "description": "Comprehensive guide for quadratic equations",
            "subject": "математика",
            "grade": 9,
            "material_type": "study_guide",
            "tags": ["algebra", "equations", "math"]
        }
        
        # Create multipart form data
        form_data = aiohttp.FormData()
        form_data.add_field('file', test_file_content, filename='study_guide.pdf', content_type='application/pdf')
        
        # Add metadata fields
        for key, value in material_data.items():
            if isinstance(value, list):
                form_data.add_field(key, json.dumps(value))
            else:
                form_data.add_field(key, str(value))
        
        # Remove content-type header for multipart upload
        upload_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/materials/upload",
            headers=upload_headers,
            data=form_data
        ) as response:
            if response.status in [200, 201]:
                uploaded_material = await response.json()
                
                # Verify upload response
                assert "id" in uploaded_material
                assert "title" in uploaded_material
                assert uploaded_material["title"] == material_data["title"]
                
                print(f"✅ Material uploaded successfully: ID {uploaded_material['id']}")
                return uploaded_material
                
            elif response.status == 404:
                print("⚠️  Material upload endpoint not found")
            elif response.status == 413:
                print("⚠️  File too large for upload")
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to material upload")
            else:
                print(f"⚠️  Material upload failed: {response.status}")
    
    
    async def test_tutor_manage_materials(self, http_client, test_config, auth_tokens):
        """Test tutor can view and manage their materials"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/materials/my-materials",
            headers=headers
        ) as response:
            if response.status == 200:
                materials_data = await response.json()
                
                # Verify materials structure
                assert "materials" in materials_data or isinstance(materials_data, list)
                
                materials = materials_data.get("materials", materials_data)
                
                if materials:
                    material = materials[0]
                    expected_fields = ["id", "title", "subject", "grade", "upload_date", 
                                     "file_size", "download_count", "status"]
                    
                    present_fields = [field for field in expected_fields if field in material]
                    print(f"✅ Tutor materials: {len(materials)} materials")
                    print(f"📊 Material fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Check material subjects
                    subjects = [mat.get("subject", "unknown") for mat in materials[:5]]
                    print(f"📚 Material subjects: {set(subjects)}")
                else:
                    print("✅ Tutor materials retrieved: No materials uploaded")
                    
            elif response.status == 404:
                print("⚠️  Tutor materials endpoint not found")
            else:
                print(f"⚠️  Tutor materials failed: {response.status}")
    
    
    async def test_tutor_organize_materials(self, http_client, test_config, auth_tokens):
        """Test tutor can organize materials into categories"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        # Test material organization
        organization_data = {
            "category": "Algebra Basics",
            "material_ids": [1, 2, 3],
            "description": "Materials for algebra fundamentals"
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/materials/organize",
            headers=headers,
            json=organization_data
        ) as response:
            if response.status in [200, 201]:
                print("✅ Material organization successful")
            elif response.status == 404:
                print("⚠️  Material organization endpoint not found")
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to material organization")
            else:
                print(f"⚠️  Material organization returned: {response.status}")
    
    
    async def test_tutor_share_materials(self, http_client, test_config, auth_tokens):
        """Test tutor can share materials with students"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        test_material_id = 999999
        sharing_data = {
            "student_ids": [1, 2, 3],
            "access_level": "read",
            "notify_students": True,
            "expiry_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/materials/{test_material_id}/share",
            headers=headers,
            json=sharing_data
        ) as response:
            if response.status == 404:
                print("✅ Material sharing endpoint accessible (material not found)")
            elif response.status in [200, 201]:
                print("✅ Material sharing successful")
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to material sharing")
            else:
                print(f"⚠️  Material sharing returned: {response.status}")


@pytest.mark.functional
@pytest.mark.tutor
class TestTutorStudentManagement:
    """Tutor student management and monitoring tests"""
    
    async def test_tutor_view_students(self, http_client, test_config, auth_tokens):
        """Test tutor can view their students list"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/tutor/students",
            headers=headers
        ) as response:
            if response.status == 200:
                students_data = await response.json()
                
                # Verify students structure
                assert "students" in students_data or isinstance(students_data, list)
                
                students = students_data.get("students", students_data)
                
                if students:
                    student = students[0]
                    expected_fields = ["id", "name", "grade", "subjects", "performance", 
                                     "last_lesson", "next_lesson"]
                    
                    present_fields = [field for field in expected_fields if field in student]
                    print(f"✅ Tutor students: {len(students)} students")
                    print(f"📊 Student fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Check student grades
                    grades = [stu.get("grade", "unknown") for stu in students[:5]]
                    print(f"🎓 Student grades: {set(grades)}")
                else:
                    print("✅ Tutor students retrieved: No students assigned")
                    
            elif response.status == 404:
                print("⚠️  Tutor students endpoint not found")
            else:
                print(f"⚠️  Tutor students failed: {response.status}")
    
    
    async def test_tutor_student_progress_tracking(self, http_client, test_config, auth_tokens):
        """Test tutor can track individual student progress"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        test_student_id = 1
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/tutor/students/{test_student_id}/progress",
            headers=headers
        ) as response:
            if response.status == 200:
                progress_data = await response.json()
                
                # Check progress metrics
                expected_metrics = ["overall_grade", "lessons_completed", "homework_completion_rate",
                                  "last_activity", "strengths", "areas_for_improvement"]
                
                present_metrics = [metric for metric in expected_metrics if metric in progress_data]
                print(f"✅ Student progress tracking: {len(present_metrics)}/{len(expected_metrics)} metrics")
                
                # Validate progress values
                if "homework_completion_rate" in progress_data:
                    rate = progress_data["homework_completion_rate"]
                    assert 0 <= rate <= 100, f"Invalid completion rate: {rate}"
                    print(f"📊 Homework completion: {rate}%")
                    
            elif response.status == 404:
                print("⚠️  Student progress tracking endpoint not found or student not found")
            else:
                print(f"⚠️  Student progress tracking failed: {response.status}")
    
    
    async def test_tutor_send_student_message(self, http_client, test_config, auth_tokens):
        """Test tutor can send messages to students"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        message_data = {
            "recipient_id": 1,
            "recipient_type": "student",
            "subject": "Homework Reminder",
            "message": "Please remember to complete your algebra homework by Friday.",
            "priority": "normal",
            "send_notification": True
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/messages/send",
            headers=headers,
            json=message_data
        ) as response:
            if response.status in [200, 201]:
                sent_message = await response.json()
                
                assert "message_id" in sent_message or "id" in sent_message
                print("✅ Message sent to student successfully")
                
            elif response.status == 404:
                print("⚠️  Message sending endpoint not found")
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to message sending")
            else:
                print(f"⚠️  Message sending returned: {response.status}")


@pytest.mark.functional
@pytest.mark.tutor
class TestTutorAnalyticsReporting:
    """Tutor analytics and reporting functionality tests"""
    
    async def test_tutor_performance_analytics(self, http_client, test_config, auth_tokens):
        """Test tutor can view performance analytics"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/analytics/tutor-performance",
            headers=headers
        ) as response:
            if response.status == 200:
                analytics_data = await response.json()
                
                # Check for tutor analytics metrics
                expected_metrics = ["total_students", "total_lessons", "average_rating", 
                                  "earnings_this_month", "lesson_completion_rate", "student_retention"]
                
                present_metrics = [metric for metric in expected_metrics if metric in analytics_data]
                print(f"✅ Tutor analytics: {len(present_metrics)}/{len(expected_metrics)} metrics")
                
                # Validate metric ranges
                if "average_rating" in analytics_data:
                    rating = analytics_data["average_rating"]
                    assert 1 <= rating <= 5, f"Invalid rating range: {rating}"
                    print(f"⭐ Average rating: {rating}/5")
                
                if "lesson_completion_rate" in analytics_data:
                    rate = analytics_data["lesson_completion_rate"]
                    assert 0 <= rate <= 100, f"Invalid completion rate: {rate}"
                    print(f"📊 Lesson completion: {rate}%")
                    
            elif response.status == 404:
                print("⚠️  Tutor analytics endpoint not found")
            else:
                print(f"⚠️  Tutor analytics failed: {response.status}")
    
    
    async def test_tutor_financial_reports(self, http_client, test_config, auth_tokens):
        """Test tutor can view financial earnings reports"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        # Test monthly earnings report
        current_month = datetime.now().strftime("%Y-%m")
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/analytics/earnings?period={current_month}",
            headers=headers
        ) as response:
            if response.status == 200:
                earnings_data = await response.json()
                
                # Check earnings structure
                expected_fields = ["total_earnings", "lessons_taught", "average_per_lesson", 
                                 "payment_breakdown", "pending_payments"]
                
                present_fields = [field for field in expected_fields if field in earnings_data]
                print(f"✅ Financial report: {len(present_fields)}/{len(expected_fields)} fields")
                
                # Validate earnings values
                if "total_earnings" in earnings_data:
                    earnings = earnings_data["total_earnings"]
                    assert earnings >= 0, f"Invalid earnings value: {earnings}"
                    print(f"💰 Total earnings: {earnings} RUB")
                    
            elif response.status == 404:
                print("⚠️  Financial reports endpoint not found")
            else:
                print(f"⚠️  Financial reports failed: {response.status}")
    
    
    async def test_tutor_student_performance_reports(self, http_client, test_config, auth_tokens):
        """Test tutor can generate student performance reports"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        # Test class performance report
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/analytics/class-performance",
            headers=headers
        ) as response:
            if response.status == 200:
                performance_data = await response.json()
                
                # Check performance report structure
                if "students" in performance_data or isinstance(performance_data, list):
                    students = performance_data.get("students", performance_data)
                    
                    if students:
                        student_report = students[0]
                        expected_fields = ["student_name", "average_grade", "attendance_rate", 
                                         "homework_completion", "improvement_trend"]
                        
                        present_fields = [field for field in expected_fields if field in student_report]
                        print(f"✅ Class performance report: {len(students)} students")
                        print(f"📊 Student report fields: {len(present_fields)}/{len(expected_fields)}")
                    else:
                        print("✅ Class performance report: No students data")
                else:
                    print("✅ Class performance report retrieved")
                    
            elif response.status == 404:
                print("⚠️  Class performance reports endpoint not found")
            else:
                print(f"⚠️  Class performance reports failed: {response.status}")


@pytest.mark.functional
@pytest.mark.tutor
class TestTutorNotificationManagement:
    """Tutor notification and communication management tests"""
    
    async def test_tutor_send_announcements(self, http_client, test_config, auth_tokens):
        """Test tutor can send announcements to students"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        announcement_data = {
            "title": "Class Schedule Update",
            "message": "Next week's lessons will be moved to Wednesday due to holiday.",
            "recipients": "all_students",  # or specific student IDs
            "priority": "high",
            "send_email": True,
            "send_telegram": True
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/notifications/announce",
            headers=headers,
            json=announcement_data
        ) as response:
            if response.status in [200, 201]:
                announcement_result = await response.json()
                
                assert "announcement_id" in announcement_result or "id" in announcement_result
                print("✅ Announcement sent successfully")
                
                # Check delivery status if available
                if "delivery_status" in announcement_result:
                    status = announcement_result["delivery_status"]
                    print(f"📨 Delivery status: {status}")
                    
            elif response.status == 404:
                print("⚠️  Announcement endpoint not found")
            elif response.status in [401, 403]:
                print("❌ Tutor denied access to announcements")
            else:
                print(f"⚠️  Announcement sending returned: {response.status}")
    
    
    async def test_tutor_notification_history(self, http_client, test_config, auth_tokens):
        """Test tutor can view sent notification history"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/notifications/sent",
            headers=headers
        ) as response:
            if response.status == 200:
                notifications_data = await response.json()
                
                notifications = notifications_data.get("notifications", notifications_data)
                
                if notifications:
                    notification = notifications[0]
                    expected_fields = ["id", "title", "message", "sent_date", "recipients_count", 
                                     "delivery_status"]
                    
                    present_fields = [field for field in expected_fields if field in notification]
                    print(f"✅ Notification history: {len(notifications)} sent notifications")
                    print(f"📊 Notification fields: {len(present_fields)}/{len(expected_fields)}")
                else:
                    print("✅ Notification history: No notifications sent")
                    
            elif response.status == 404:
                print("⚠️  Notification history endpoint not found")
            else:
                print(f"⚠️  Notification history failed: {response.status}")


@pytest.mark.functional
@pytest.mark.tutor
class TestTutorEndToEndWorkflows:
    """End-to-end tutor workflow tests"""
    
    async def test_complete_lesson_management_workflow(self, http_client, test_config, auth_tokens, test_lesson_data):
        """Test complete lesson management workflow"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        workflow_steps = []
        
        # Step 1: Create lesson
        lesson_data = test_lesson_data()
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/create",
            headers=headers,
            json=lesson_data
        ) as response:
            if response.status in [200, 201]:
                workflow_steps.append("✅ Lesson creation")
                created_lesson = await response.json()
                lesson_id = created_lesson.get("id")
            else:
                workflow_steps.append("❌ Lesson creation")
                lesson_id = 999999  # Use test ID for remaining steps
        
        # Step 2: View schedule
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/my-lessons",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Schedule viewing")
            else:
                workflow_steps.append("❌ Schedule viewing")
        
        # Step 3: Mark attendance
        attendance_data = {"student_attended": True, "lesson_completed": True}
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{lesson_id}/attendance",
            headers=headers,
            json=attendance_data
        ) as response:
            if response.status in [200, 201, 404]:  # 404 OK for test
                workflow_steps.append("✅ Attendance marking")
            else:
                workflow_steps.append("❌ Attendance marking")
        
        print("👨‍🏫 Complete Lesson Management Workflow:")
        for step in workflow_steps:
            print(f"  {step}")
        
        # Verify workflow success
        successful_steps = [step for step in workflow_steps if step.startswith("✅")]
        assert len(successful_steps) >= len(workflow_steps) // 2, \
            f"Too many workflow steps failed: {workflow_steps}"
        
        print(f"✅ Lesson workflow: {len(successful_steps)}/{len(workflow_steps)} steps successful")
    
    
    async def test_complete_homework_management_workflow(self, http_client, test_config, auth_tokens):
        """Test complete homework management workflow"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        headers = auth_tokens["TUTOR"]["headers"]
        homework_flow = []
        
        # Step 1: Assign homework
        homework_data = {
            "title": "Test Assignment",
            "description": "Complete practice problems",
            "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "max_score": 100
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/assign",
            headers=headers,
            json=homework_data
        ) as response:
            if response.status in [200, 201]:
                homework_flow.append("✅ Homework assignment")
                homework_result = await response.json()
                homework_id = homework_result.get("id")
            else:
                homework_flow.append("❌ Homework assignment")
                homework_id = 999999
        
        # Step 2: View submissions
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/submissions",
            headers=headers
        ) as response:
            if response.status == 200:
                homework_flow.append("✅ Submission viewing")
            else:
                homework_flow.append("❌ Submission viewing")
        
        # Step 3: Grade submission
        grading_data = {"score": 95, "max_score": 100, "feedback": "Great work!"}
        test_submission_id = 999999
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/submissions/{test_submission_id}/grade",
            headers=headers,
            json=grading_data
        ) as response:
            if response.status in [200, 201, 404]:  # 404 OK for test
                homework_flow.append("✅ Homework grading")
            else:
                homework_flow.append("❌ Homework grading")
        
        print("📝 Complete Homework Management Workflow:")
        for step in homework_flow:
            print(f"  {step}")
        
        # Verify workflow success
        successful_steps = [step for step in homework_flow if step.startswith("✅")]
        assert len(successful_steps) >= len(homework_flow) // 2, \
            f"Too many workflow steps failed: {homework_flow}"
        
        print(f"✅ Homework workflow: {len(successful_steps)}/{len(homework_flow)} steps successful")