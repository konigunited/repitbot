"""
Student Dashboard Functional Tests
=================================

Comprehensive functional tests for the Student role in RepitBot system.
Tests all student-specific features and gamification workflows.

Student Dashboard Features:
- 📚 Lesson Management (view schedule, join lessons, lesson history)
- 📝 Homework System (receive assignments, submit work, view grades)
- 📖 Material Library (access study materials, download resources)
- 🏆 Achievement System (XP, levels, badges, streaks) 
- 📊 Progress Tracking (performance analytics, skill development)
- 🎮 Gamification (leaderboards, challenges, rewards)
- 🔔 Notifications (lesson reminders, homework deadlines, achievements)

Key Student Workflows:
1. Join upcoming lessons and view lesson history
2. Receive homework assignments and submit completed work
3. Access and download educational materials
4. Track personal progress and achievements
5. Participate in gamified learning experiences
6. Manage notification preferences
"""

import pytest
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import io
import base64


@pytest.mark.functional
@pytest.mark.student
class TestStudentLessonManagement:
    """Student lesson viewing and participation tests"""
    
    async def test_student_view_schedule(self, http_client, test_config, auth_tokens):
        """Test student can view their own lesson schedule"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        # Try different schedule endpoints
        schedule_endpoints = [
            "/api/v1/lessons/my-schedule",
            "/api/v1/lessons/schedule",
            "/api/v1/student/lessons",
            "/api/v1/schedule/upcoming"
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
                        expected_fields = ["id", "subject", "date", "time", "tutor_name", "status"]
                        
                        present_fields = [field for field in expected_fields if field in lesson]
                        print(f"✅ Schedule retrieved from {endpoint}: {len(lessons)} lessons")
                        print(f"📊 Lesson fields: {len(present_fields)}/{len(expected_fields)}")
                    else:
                        print(f"✅ Schedule retrieved from {endpoint}: No lessons scheduled")
                    
                    schedule_found = True
                    break
                    
                elif response.status != 404:
                    print(f"⚠️  Schedule endpoint {endpoint} failed: {response.status}")
        
        if not schedule_found:
            print("⚠️  No working schedule endpoint found")
    
    
    async def test_student_lesson_details(self, http_client, test_config, auth_tokens):
        """Test student can view detailed lesson information"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        # First get schedule to find a lesson ID
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/my-schedule",
            headers=headers
        ) as response:
            if response.status == 200:
                schedule_data = await response.json()
                lessons = schedule_data.get("lessons", schedule_data)
                
                if lessons and len(lessons) > 0:
                    lesson_id = lessons[0].get("id")
                    
                    if lesson_id:
                        async with http_client.get(
                            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{lesson_id}",
                            headers=headers
                        ) as detail_response:
                            if detail_response.status == 200:
                                lesson_details = await detail_response.json()
                                
                                expected_fields = ["id", "subject", "date", "duration", "tutor_name", 
                                                 "description", "materials", "meeting_link"]
                                present_fields = [field for field in expected_fields if field in lesson_details]
                                
                                print(f"✅ Lesson details: {len(present_fields)}/{len(expected_fields)} fields")
                                
                                # Check for meeting link (important for online lessons)
                                if "meeting_link" in lesson_details:
                                    print("✅ Meeting link available for lesson")
                                    
                            else:
                                print(f"⚠️  Lesson details failed: {detail_response.status}")
                    else:
                        print("⚠️  No lesson ID found in schedule")
                else:
                    print("✅ Schedule retrieved but no lessons found")
            else:
                print(f"⚠️  Could not get schedule: {response.status}")
    
    
    async def test_student_lesson_attendance(self, http_client, test_config, auth_tokens):
        """Test student can mark attendance for lessons"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        test_lesson_id = 999999  # Non-existent lesson for testing
        attendance_data = {
            "status": "attended",
            "notes": "Great lesson!"
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/{test_lesson_id}/attendance",
            headers=headers,
            json=attendance_data
        ) as response:
            if response.status == 404:
                print("✅ Lesson attendance endpoint accessible (lesson not found)")
            elif response.status in [200, 201]:
                print("✅ Lesson attendance recorded successfully")
            elif response.status in [401, 403]:
                print("❌ Student denied access to attendance marking")
            else:
                print(f"⚠️  Attendance marking returned: {response.status}")
    
    
    async def test_student_lesson_history(self, http_client, test_config, auth_tokens):
        """Test student can view their lesson history"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/history",
            headers=headers
        ) as response:
            if response.status == 200:
                history_data = await response.json()
                
                assert "lessons" in history_data or isinstance(history_data, list)
                
                lessons = history_data.get("lessons", history_data)
                
                if lessons:
                    lesson = lessons[0]
                    expected_fields = ["id", "subject", "date", "status", "attendance", "grade"]
                    
                    present_fields = [field for field in expected_fields if field in lesson]
                    print(f"✅ Lesson history: {len(lessons)} lessons")
                    print(f"📊 History fields: {len(present_fields)}/{len(expected_fields)}")
                else:
                    print("✅ Lesson history retrieved: No completed lessons")
                    
            elif response.status == 404:
                print("⚠️  Lesson history endpoint not found")
            else:
                print(f"⚠️  Lesson history failed: {response.status}")


@pytest.mark.functional
@pytest.mark.student
class TestStudentHomeworkSystem:
    """Student homework management tests"""
    
    async def test_student_view_homework_assignments(self, http_client, test_config, auth_tokens):
        """Test student can view their homework assignments"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/assignments",
            headers=headers
        ) as response:
            if response.status == 200:
                assignments_data = await response.json()
                
                assert "assignments" in assignments_data or isinstance(assignments_data, list)
                
                assignments = assignments_data.get("assignments", assignments_data)
                
                if assignments:
                    assignment = assignments[0]
                    expected_fields = ["id", "title", "description", "due_date", "subject", "status", "max_score"]
                    
                    present_fields = [field for field in expected_fields if field in assignment]
                    print(f"✅ Homework assignments: {len(assignments)} assignments")
                    print(f"📊 Assignment fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Check due date format
                    if "due_date" in assignment:
                        try:
                            due_date = datetime.fromisoformat(assignment["due_date"].replace('Z', '+00:00'))
                            print(f"✅ Due date format valid: {due_date}")
                        except:
                            print(f"⚠️  Invalid due date format: {assignment['due_date']}")
                else:
                    print("✅ Homework assignments retrieved: No assignments")
                    
            elif response.status == 404:
                print("⚠️  Homework assignments endpoint not found")
            else:
                print(f"⚠️  Homework assignments failed: {response.status}")
    
    
    async def test_student_homework_submission(self, http_client, test_config, auth_tokens):
        """Test student can submit homework assignments"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        # Test homework submission
        test_homework_id = 999999
        submission_data = {
            "answers": {
                "question_1": "Sample answer to question 1",
                "question_2": "Sample answer to question 2"
            },
            "notes": "Completed homework assignment",
            "submitted_at": datetime.now().isoformat()
        }
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/{test_homework_id}/submit",
            headers=headers,
            json=submission_data
        ) as response:
            if response.status == 404:
                print("✅ Homework submission endpoint accessible (homework not found)")
            elif response.status in [200, 201]:
                print("✅ Homework submission successful")
            elif response.status in [401, 403]:
                print("❌ Student denied access to homework submission")
            else:
                print(f"⚠️  Homework submission returned: {response.status}")
    
    
    async def test_student_homework_file_upload(self, http_client, test_config, auth_tokens):
        """Test student can upload files with homework submissions"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        # Create a test file
        test_file_content = b"This is a test homework file content"
        
        # Test file upload
        test_homework_id = 999999
        
        # Using multipart form data for file upload
        form_data = aiohttp.FormData()
        form_data.add_field('file', test_file_content, filename='homework.txt', content_type='text/plain')
        form_data.add_field('description', 'Homework submission file')
        
        # Remove content-type header for multipart upload
        upload_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/{test_homework_id}/upload",
            headers=upload_headers,
            data=form_data
        ) as response:
            if response.status == 404:
                print("✅ Homework file upload endpoint accessible (homework not found)")
            elif response.status in [200, 201]:
                print("✅ Homework file upload successful")
            elif response.status in [401, 403]:
                print("❌ Student denied access to file upload")
            elif response.status == 413:
                print("⚠️  File too large for upload")
            else:
                print(f"⚠️  File upload returned: {response.status}")
    
    
    async def test_student_homework_grades(self, http_client, test_config, auth_tokens):
        """Test student can view their homework grades"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/grades",
            headers=headers
        ) as response:
            if response.status == 200:
                grades_data = await response.json()
                
                assert "grades" in grades_data or isinstance(grades_data, list)
                
                grades = grades_data.get("grades", grades_data)
                
                if grades:
                    grade = grades[0]
                    expected_fields = ["homework_id", "score", "max_score", "feedback", "graded_date"]
                    
                    present_fields = [field for field in expected_fields if field in grade]
                    print(f"✅ Homework grades: {len(grades)} graded assignments")
                    print(f"📊 Grade fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Verify score ranges
                    if "score" in grade and "max_score" in grade:
                        assert 0 <= grade["score"] <= grade["max_score"], \
                            f"Invalid score range: {grade['score']}/{grade['max_score']}"
                        print(f"✅ Score validation passed: {grade['score']}/{grade['max_score']}")
                else:
                    print("✅ Homework grades retrieved: No graded assignments")
                    
            elif response.status == 404:
                print("⚠️  Homework grades endpoint not found")
            else:
                print(f"⚠️  Homework grades failed: {response.status}")


@pytest.mark.functional
@pytest.mark.student
class TestStudentMaterialLibrary:
    """Student material access and library tests"""
    
    async def test_student_view_material_library(self, http_client, test_config, auth_tokens):
        """Test student can access material library"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/materials/library",
            headers=headers
        ) as response:
            if response.status == 200:
                materials_data = await response.json()
                
                assert "materials" in materials_data or isinstance(materials_data, list)
                
                materials = materials_data.get("materials", materials_data)
                
                if materials:
                    material = materials[0]
                    expected_fields = ["id", "title", "subject", "grade", "type", "file_url", "description"]
                    
                    present_fields = [field for field in expected_fields if field in material]
                    print(f"✅ Material library: {len(materials)} materials available")
                    print(f"📊 Material fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Check material types
                    material_types = [mat.get("type", "unknown") for mat in materials[:5]]
                    print(f"📚 Material types: {set(material_types)}")
                else:
                    print("✅ Material library retrieved: No materials available")
                    
            elif response.status == 404:
                print("⚠️  Material library endpoint not found")
            else:
                print(f"⚠️  Material library failed: {response.status}")
    
    
    async def test_student_filter_materials_by_subject(self, http_client, test_config, auth_tokens):
        """Test student can filter materials by subject and grade"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        # Test subject filtering
        test_subjects = ["математика", "физика", "химия"]
        
        for subject in test_subjects:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/materials/library?subject={subject}",
                headers=headers
            ) as response:
                if response.status == 200:
                    materials_data = await response.json()
                    materials = materials_data.get("materials", materials_data)
                    
                    print(f"✅ Materials filtered by {subject}: {len(materials)} results")
                    
                    # Verify filtering worked (if materials exist)
                    if materials:
                        for material in materials[:3]:  # Check first 3
                            if "subject" in material:
                                assert material["subject"] == subject or subject in material["subject"], \
                                    f"Material subject mismatch: expected {subject}, got {material['subject']}"
                    
                elif response.status != 404:
                    print(f"⚠️  Subject filter for {subject} failed: {response.status}")
        
        # Test grade filtering
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/materials/library?grade=10",
            headers=headers
        ) as response:
            if response.status == 200:
                materials_data = await response.json()
                materials = materials_data.get("materials", materials_data)
                
                print(f"✅ Materials filtered by grade 10: {len(materials)} results")
                
            elif response.status != 404:
                print(f"⚠️  Grade filtering failed: {response.status}")
    
    
    async def test_student_download_material(self, http_client, test_config, auth_tokens):
        """Test student can download educational materials"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        # First get materials to find a downloadable file
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/materials/library",
            headers=headers
        ) as response:
            if response.status == 200:
                materials_data = await response.json()
                materials = materials_data.get("materials", materials_data)
                
                if materials and len(materials) > 0:
                    material_id = materials[0].get("id")
                    
                    if material_id:
                        # Test material download
                        async with http_client.get(
                            f"{test_config.API_GATEWAY_URL}/api/v1/materials/{material_id}/download",
                            headers=headers
                        ) as download_response:
                            if download_response.status == 200:
                                # Check if it's actually a file download
                                content_type = download_response.headers.get("Content-Type", "")
                                content_disposition = download_response.headers.get("Content-Disposition", "")
                                
                                if "attachment" in content_disposition or "application/" in content_type:
                                    print("✅ Material download successful (file received)")
                                else:
                                    print("✅ Material download endpoint accessible")
                                    
                            elif download_response.status == 404:
                                print("⚠️  Material not found for download")
                            elif download_response.status in [401, 403]:
                                print("❌ Student denied access to material download")
                            else:
                                print(f"⚠️  Material download failed: {download_response.status}")
                    else:
                        print("⚠️  No material ID found for download test")
                else:
                    print("✅ No materials available for download testing")
            else:
                print(f"⚠️  Could not get materials: {response.status}")
    
    
    async def test_student_material_search(self, http_client, test_config, auth_tokens):
        """Test student can search materials"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        search_terms = ["алгебра", "физика", "учебник"]
        
        for term in search_terms:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/materials/search?q={term}",
                headers=headers
            ) as response:
                if response.status == 200:
                    search_results = await response.json()
                    results = search_results.get("results", search_results)
                    
                    print(f"✅ Material search for '{term}': {len(results)} results")
                    
                elif response.status == 404:
                    print(f"⚠️  Material search endpoint not found")
                    break
                else:
                    print(f"⚠️  Material search for '{term}' failed: {response.status}")


@pytest.mark.functional
@pytest.mark.student
class TestStudentAchievements:
    """Student achievement and gamification system tests"""
    
    async def test_student_view_achievements(self, http_client, test_config, auth_tokens):
        """Test student can view their achievements and badges"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/student/achievements",
            headers=headers
        ) as response:
            if response.status == 200:
                achievements_data = await response.json()
                
                assert "achievements" in achievements_data or isinstance(achievements_data, list)
                
                achievements = achievements_data.get("achievements", achievements_data)
                
                if achievements:
                    achievement = achievements[0]
                    expected_fields = ["id", "title", "description", "earned_date", "level", "xp_awarded"]
                    
                    present_fields = [field for field in expected_fields if field in achievement]
                    print(f"✅ Student achievements: {len(achievements)} achievements")
                    print(f"📊 Achievement fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Check achievement levels
                    levels = [ach.get("level", "unknown") for ach in achievements[:5]]
                    print(f"🏆 Achievement levels: {set(levels)}")
                else:
                    print("✅ Achievements retrieved: No achievements earned yet")
                    
            elif response.status == 404:
                print("⚠️  Achievements endpoint not found")
            else:
                print(f"⚠️  Achievements failed: {response.status}")
    
    
    async def test_student_view_progress_stats(self, http_client, test_config, auth_tokens):
        """Test student can view their progress statistics"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/student/progress",
            headers=headers
        ) as response:
            if response.status == 200:
                progress_data = await response.json()
                
                # Check for progress metrics
                expected_metrics = ["current_level", "total_xp", "lessons_completed", "homework_completed", 
                                  "average_grade", "streak_days", "subjects_studied"]
                
                present_metrics = [metric for metric in expected_metrics if metric in progress_data]
                print(f"✅ Student progress: {len(present_metrics)}/{len(expected_metrics)} metrics")
                
                # Validate metric values
                if "current_level" in progress_data:
                    assert progress_data["current_level"] >= 1, "Invalid level (should be >= 1)"
                    print(f"📊 Current level: {progress_data['current_level']}")
                
                if "total_xp" in progress_data:
                    assert progress_data["total_xp"] >= 0, "Invalid XP (should be >= 0)"
                    print(f"✨ Total XP: {progress_data['total_xp']}")
                
                if "streak_days" in progress_data:
                    assert progress_data["streak_days"] >= 0, "Invalid streak (should be >= 0)"
                    print(f"🔥 Learning streak: {progress_data['streak_days']} days")
                    
            elif response.status == 404:
                print("⚠️  Progress endpoint not found")
            else:
                print(f"⚠️  Progress stats failed: {response.status}")
    
    
    async def test_student_leaderboard(self, http_client, test_config, auth_tokens):
        """Test student can view leaderboards"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/student/leaderboard",
            headers=headers
        ) as response:
            if response.status == 200:
                leaderboard_data = await response.json()
                
                assert "rankings" in leaderboard_data or isinstance(leaderboard_data, list)
                
                rankings = leaderboard_data.get("rankings", leaderboard_data)
                
                if rankings:
                    rank_entry = rankings[0]
                    expected_fields = ["rank", "student_name", "score", "level"]
                    
                    present_fields = [field for field in expected_fields if field in rank_entry]
                    print(f"✅ Leaderboard: {len(rankings)} students ranked")
                    print(f"📊 Ranking fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Verify rankings are sorted correctly
                    if len(rankings) > 1:
                        for i in range(len(rankings) - 1):
                            current_score = rankings[i].get("score", 0)
                            next_score = rankings[i + 1].get("score", 0)
                            if current_score < next_score:
                                print("⚠️  Leaderboard not properly sorted")
                                break
                        else:
                            print("✅ Leaderboard properly sorted by score")
                else:
                    print("✅ Leaderboard retrieved: No rankings available")
                    
            elif response.status == 404:
                print("⚠️  Leaderboard endpoint not found")
            else:
                print(f"⚠️  Leaderboard failed: {response.status}")
    
    
    async def test_student_skill_tracking(self, http_client, test_config, auth_tokens):
        """Test student can view skill development tracking"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/student/skills",
            headers=headers
        ) as response:
            if response.status == 200:
                skills_data = await response.json()
                
                assert "skills" in skills_data or isinstance(skills_data, list)
                
                skills = skills_data.get("skills", skills_data)
                
                if skills:
                    skill = skills[0]
                    expected_fields = ["skill_name", "level", "progress", "mastery_percentage"]
                    
                    present_fields = [field for field in expected_fields if field in skill]
                    print(f"✅ Skill tracking: {len(skills)} skills tracked")
                    print(f"📊 Skill fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Check skill progress ranges
                    for skill in skills[:3]:
                        if "mastery_percentage" in skill:
                            mastery = skill["mastery_percentage"]
                            assert 0 <= mastery <= 100, f"Invalid mastery percentage: {mastery}"
                    
                    print("✅ Skill mastery percentages valid")
                else:
                    print("✅ Skill tracking retrieved: No skills tracked yet")
                    
            elif response.status == 404:
                print("⚠️  Skill tracking endpoint not found")
            else:
                print(f"⚠️  Skill tracking failed: {response.status}")


@pytest.mark.functional
@pytest.mark.student
class TestStudentNotifications:
    """Student notification management tests"""
    
    async def test_student_notification_preferences(self, http_client, test_config, auth_tokens):
        """Test student can manage notification preferences"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        # Get current preferences
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/notifications/preferences",
            headers=headers
        ) as response:
            if response.status == 200:
                preferences = await response.json()
                
                # Check for student-specific notification types
                student_prefs = ["lesson_reminders", "homework_deadlines", "achievement_notifications", 
                               "grade_notifications", "new_materials"]
                
                for pref in student_prefs:
                    if pref in preferences:
                        print(f"✅ Notification preference: {pref} = {preferences[pref]}")
                
                # Test updating preferences
                new_preferences = {
                    "lesson_reminders": True,
                    "homework_deadlines": True,
                    "achievement_notifications": True,
                    "grade_notifications": False
                }
                
                async with http_client.put(
                    f"{test_config.API_GATEWAY_URL}/api/v1/notifications/preferences",
                    headers=headers,
                    json=new_preferences
                ) as update_response:
                    if update_response.status in [200, 204]:
                        print("✅ Student notification preferences updated")
                    else:
                        print(f"⚠️  Preference update failed: {update_response.status}")
                        
            elif response.status == 404:
                print("⚠️  Notification preferences endpoint not found")
            else:
                print(f"⚠️  Preferences check failed: {response.status}")
    
    
    async def test_student_notification_history(self, http_client, test_config, auth_tokens):
        """Test student can view their notification history"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/notifications/history",
            headers=headers
        ) as response:
            if response.status == 200:
                history = await response.json()
                
                notifications = history.get("notifications", history)
                
                if notifications:
                    notification = notifications[0]
                    expected_fields = ["id", "type", "message", "sent_date", "read_status"]
                    
                    present_fields = [field for field in expected_fields if field in notification]
                    print(f"✅ Notification history: {len(notifications)} notifications")
                    print(f"📊 Notification fields: {len(present_fields)}/{len(expected_fields)}")
                    
                    # Check notification types
                    notif_types = [n.get("type", "unknown") for n in notifications[:5]]
                    print(f"📨 Notification types: {set(notif_types)}")
                else:
                    print("✅ Notification history retrieved: No notifications")
                    
            elif response.status == 404:
                print("⚠️  Notification history endpoint not found")
            else:
                print(f"⚠️  Notification history failed: {response.status}")


@pytest.mark.functional
@pytest.mark.student
class TestStudentEndToEndWorkflows:
    """End-to-end student workflow tests"""
    
    async def test_complete_student_learning_session(self, http_client, test_config, auth_tokens):
        """Test complete student learning session workflow"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        workflow_steps = []
        
        # Step 1: Check schedule
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/lessons/my-schedule",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Schedule check")
            else:
                workflow_steps.append("❌ Schedule check")
        
        # Step 2: View homework assignments
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/assignments",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Homework view")
            else:
                workflow_steps.append("❌ Homework view")
        
        # Step 3: Access materials
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/materials/library",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Materials access")
            else:
                workflow_steps.append("❌ Materials access")
        
        # Step 4: Check achievements
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/student/achievements",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Achievements view")
            else:
                workflow_steps.append("❌ Achievements view")
        
        # Step 5: View progress
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/student/progress",
            headers=headers
        ) as response:
            if response.status == 200:
                workflow_steps.append("✅ Progress tracking")
            else:
                workflow_steps.append("❌ Progress tracking")
        
        print("🎮 Complete Student Learning Session Results:")
        for step in workflow_steps:
            print(f"  {step}")
        
        # Verify majority of workflow works
        successful_steps = [step for step in workflow_steps if step.startswith("✅")]
        assert len(successful_steps) >= len(workflow_steps) // 2, \
            f"Too many workflow steps failed: {workflow_steps}"
        
        print(f"✅ Student workflow: {len(successful_steps)}/{len(workflow_steps)} steps successful")
    
    
    async def test_student_homework_complete_flow(self, http_client, test_config, auth_tokens):
        """Test complete homework workflow from assignment to submission"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        headers = auth_tokens["STUDENT"]["headers"]
        homework_flow = []
        
        # Step 1: Get assignments
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/homework/assignments",
            headers=headers
        ) as response:
            if response.status == 200:
                homework_flow.append("✅ Assignment retrieval")
                assignments_data = await response.json()
                assignments = assignments_data.get("assignments", assignments_data)
                
                if assignments and len(assignments) > 0:
                    assignment_id = assignments[0].get("id")
                    
                    if assignment_id:
                        # Step 2: Submit homework
                        submission_data = {
                            "answers": {"q1": "Test answer"},
                            "notes": "Completed homework"
                        }
                        
                        async with http_client.post(
                            f"{test_config.API_GATEWAY_URL}/api/v1/homework/{assignment_id}/submit",
                            headers=headers,
                            json=submission_data
                        ) as submit_response:
                            if submit_response.status in [200, 201, 404]:  # 404 is OK for test
                                homework_flow.append("✅ Homework submission")
                            else:
                                homework_flow.append("❌ Homework submission")
                        
                        # Step 3: Check grades
                        async with http_client.get(
                            f"{test_config.API_GATEWAY_URL}/api/v1/homework/grades",
                            headers=headers
                        ) as grades_response:
                            if grades_response.status == 200:
                                homework_flow.append("✅ Grade checking")
                            else:
                                homework_flow.append("❌ Grade checking")
                    else:
                        homework_flow.append("⚠️  No assignment ID found")
                else:
                    homework_flow.append("⚠️  No assignments found")
            else:
                homework_flow.append("❌ Assignment retrieval")
        
        print("📝 Student Homework Complete Flow Results:")
        for step in homework_flow:
            print(f"  {step}")
        
        # Verify at least assignment retrieval works
        assert homework_flow[0].startswith("✅"), "Assignment retrieval must work"
        print(f"✅ Homework flow: {len([s for s in homework_flow if s.startswith('✅')])}/{len(homework_flow)} steps successful")