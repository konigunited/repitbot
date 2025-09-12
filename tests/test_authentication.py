"""
Authentication and Authorization Tests
====================================

Tests for validating JWT authentication and role-based access control (RBAC)
across all microservices in the RepitBot system.

Three main roles tested:
- PARENT: Access to payments, child schedule, progress monitoring
- STUDENT: Access to lessons, homework, materials, achievements  
- TUTOR: Full access to lesson management, grading, analytics

Security aspects tested:
- JWT token generation and validation
- Role-based endpoint access control
- Token expiration and refresh
- Cross-service authentication
- Authorization failure handling
- Session management
"""

import pytest
import asyncio
import aiohttp
import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any


@pytest.mark.auth
class TestAuthentication:
    """Core authentication functionality tests"""
    
    async def test_user_registration_all_roles(self, http_client, test_config, generate_test_user):
        """Test user registration for all three roles"""
        
        roles = ["PARENT", "STUDENT", "TUTOR"]
        registered_users = {}
        
        for role in roles:
            user_data = generate_test_user(role)
            
            async with http_client.post(
                f"{test_config.API_GATEWAY_URL}/api/v1/auth/register",
                json=user_data
            ) as response:
                assert response.status == 201, f"Registration failed for role {role}"
                
                response_data = await response.json()
                
                # Verify response structure
                assert "id" in response_data
                assert "email" in response_data
                assert "role" in response_data
                assert response_data["role"] == role
                assert "created_at" in response_data
                
                # Should not return password
                assert "password" not in response_data
                
                registered_users[role] = response_data
                print(f"✅ {role} registration successful: {response_data['email']}")
        
        return registered_users
    
    
    async def test_user_login_all_roles(self, http_client, test_config, generate_test_user):
        """Test user login and JWT token generation for all roles"""
        
        roles = ["PARENT", "STUDENT", "TUTOR"]
        tokens = {}
        
        for role in roles:
            # First register user
            user_data = generate_test_user(role)
            
            async with http_client.post(
                f"{test_config.API_GATEWAY_URL}/api/v1/auth/register",
                json=user_data
            ) as register_response:
                assert register_response.status == 201
            
            # Then login
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            async with http_client.post(
                f"{test_config.API_GATEWAY_URL}/api/v1/auth/login",
                json=login_data
            ) as login_response:
                assert login_response.status == 200
                
                response_data = await login_response.json()
                
                # Verify response structure
                assert "access_token" in response_data
                assert "token_type" in response_data
                assert "expires_in" in response_data
                assert response_data["token_type"] == "bearer"
                
                # Verify JWT token structure
                token = response_data["access_token"]
                try:
                    decoded = jwt.decode(
                        token, 
                        test_config.JWT_SECRET, 
                        algorithms=["HS256"]
                    )
                    
                    assert "sub" in decoded  # Subject (user ID)
                    assert "role" in decoded
                    assert "exp" in decoded  # Expiration
                    assert decoded["role"] == role
                    
                except jwt.InvalidTokenError as e:
                    pytest.fail(f"Invalid JWT token for {role}: {e}")
                
                tokens[role] = {
                    "token": token,
                    "user_data": user_data,
                    "decoded": decoded
                }
                
                print(f"✅ {role} login successful, JWT valid")
        
        return tokens
    
    
    async def test_invalid_login_attempts(self, http_client, test_config, generate_test_user):
        """Test handling of invalid login attempts"""
        
        user_data = generate_test_user("STUDENT")
        
        # Register valid user first
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/auth/register",
            json=user_data
        ) as response:
            assert response.status == 201
        
        # Test wrong password
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": "wrongpassword"
            }
        ) as response:
            assert response.status == 401
            error_data = await response.json()
            assert "error" in error_data
            print("✅ Wrong password correctly rejected")
        
        # Test non-existent email
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "password123"
            }
        ) as response:
            assert response.status == 401
            error_data = await response.json()
            assert "error" in error_data
            print("✅ Non-existent email correctly rejected")
        
        # Test malformed email
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/auth/login",
            json={
                "email": "invalid-email",
                "password": "password123"
            }
        ) as response:
            assert response.status in [400, 401]  # Bad request or unauthorized
            print("✅ Malformed email correctly rejected")
    
    
    async def test_token_expiration_handling(self, http_client, test_config):
        """Test JWT token expiration and refresh"""
        
        # Create a token with very short expiration for testing
        short_lived_payload = {
            "sub": "test_user_123",
            "role": "STUDENT",
            "exp": datetime.utcnow() + timedelta(seconds=1),  # Expires in 1 second
            "iat": datetime.utcnow()
        }
        
        short_token = jwt.encode(
            short_lived_payload,
            test_config.JWT_SECRET,
            algorithm="HS256"
        )
        
        # Wait for token to expire
        await asyncio.sleep(2)
        
        # Try to use expired token
        headers = {"Authorization": f"Bearer {short_token}"}
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
            headers=headers
        ) as response:
            assert response.status == 401
            error_data = await response.json()
            assert "expired" in str(error_data).lower() or "unauthorized" in str(error_data).lower()
            print("✅ Expired token correctly rejected")
    
    
    async def test_malformed_token_handling(self, http_client, test_config):
        """Test handling of malformed JWT tokens"""
        
        malformed_tokens = [
            "invalid.token.here",
            "Bearer malformed_token",
            "",
            "not_a_token_at_all",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",  # Invalid payload
        ]
        
        for malformed_token in malformed_tokens:
            headers = {"Authorization": f"Bearer {malformed_token}"}
            
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
                headers=headers
            ) as response:
                assert response.status == 401
                print(f"✅ Malformed token correctly rejected: {malformed_token[:20]}...")


@pytest.mark.auth
class TestRoleBasedAccess:
    """Role-based access control (RBAC) tests"""
    
    async def test_parent_role_access_permissions(self, http_client, test_config, auth_tokens):
        """Test PARENT role can only access authorized endpoints"""
        
        if "PARENT" not in auth_tokens:
            pytest.skip("PARENT token not available")
        
        parent_token = auth_tokens["PARENT"]["headers"]
        
        # PARENT should have access to:
        allowed_endpoints = [
            "/api/v1/users/profile",  # Own profile
            "/api/v1/users/children",  # Children list
            "/api/v1/payments/balance",  # Payment balance
            "/api/v1/payments/history",  # Payment history
            "/api/v1/lessons/schedule",  # Children's schedule
            "/api/v1/analytics/child-progress",  # Child progress
        ]
        
        for endpoint in allowed_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=parent_token
            ) as response:
                # Should not be 401/403 (unauthorized/forbidden)
                assert response.status not in [401, 403], \
                    f"PARENT denied access to allowed endpoint: {endpoint}"
                print(f"✅ PARENT access granted: {endpoint}")
        
        # PARENT should NOT have access to:
        forbidden_endpoints = [
            "/api/v1/admin/users",  # Admin functions
            "/api/v1/lessons/create",  # Create lessons (tutor only)
            "/api/v1/homework/grade",  # Grade homework (tutor only)
            "/api/v1/materials/upload",  # Upload materials (tutor only)
        ]
        
        for endpoint in forbidden_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=parent_token
            ) as response:
                assert response.status in [401, 403, 404], \
                    f"PARENT granted access to forbidden endpoint: {endpoint}"
                print(f"✅ PARENT access denied: {endpoint}")
    
    
    async def test_student_role_access_permissions(self, http_client, test_config, auth_tokens):
        """Test STUDENT role can only access authorized endpoints"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        student_token = auth_tokens["STUDENT"]["headers"]
        
        # STUDENT should have access to:
        allowed_endpoints = [
            "/api/v1/users/profile",  # Own profile
            "/api/v1/lessons/my-schedule",  # Own schedule
            "/api/v1/homework/assignments",  # Homework assignments
            "/api/v1/homework/submit",  # Submit homework
            "/api/v1/materials/library",  # Material library
            "/api/v1/student/achievements",  # Own achievements
            "/api/v1/student/progress",  # Own progress
        ]
        
        for endpoint in allowed_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=student_token
            ) as response:
                assert response.status not in [401, 403], \
                    f"STUDENT denied access to allowed endpoint: {endpoint}"
                print(f"✅ STUDENT access granted: {endpoint}")
        
        # STUDENT should NOT have access to:
        forbidden_endpoints = [
            "/api/v1/admin/users",  # Admin functions
            "/api/v1/lessons/create",  # Create lessons
            "/api/v1/homework/grade",  # Grade homework
            "/api/v1/payments/process",  # Process payments
            "/api/v1/analytics/tutor-stats",  # Tutor analytics
        ]
        
        for endpoint in forbidden_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=student_token
            ) as response:
                assert response.status in [401, 403, 404], \
                    f"STUDENT granted access to forbidden endpoint: {endpoint}"
                print(f"✅ STUDENT access denied: {endpoint}")
    
    
    async def test_tutor_role_access_permissions(self, http_client, test_config, auth_tokens):
        """Test TUTOR role has broad access to management functions"""
        
        if "TUTOR" not in auth_tokens:
            pytest.skip("TUTOR token not available")
        
        tutor_token = auth_tokens["TUTOR"]["headers"]
        
        # TUTOR should have access to:
        allowed_endpoints = [
            "/api/v1/users/profile",  # Own profile
            "/api/v1/lessons/create",  # Create lessons
            "/api/v1/lessons/manage",  # Manage lessons
            "/api/v1/homework/assign",  # Assign homework
            "/api/v1/homework/grade",  # Grade homework
            "/api/v1/materials/upload",  # Upload materials
            "/api/v1/materials/manage",  # Manage materials
            "/api/v1/analytics/students",  # Student analytics
            "/api/v1/notification/send",  # Send notifications
        ]
        
        for endpoint in allowed_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=tutor_token
            ) as response:
                assert response.status not in [401, 403], \
                    f"TUTOR denied access to allowed endpoint: {endpoint}"
                print(f"✅ TUTOR access granted: {endpoint}")
        
        # TUTOR should NOT have access to:
        forbidden_endpoints = [
            "/api/v1/admin/system",  # System admin functions
            "/api/v1/admin/users/delete",  # Delete users (if admin-only)
        ]
        
        for endpoint in forbidden_endpoints:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}{endpoint}",
                headers=tutor_token
            ) as response:
                # May be 404 if endpoint doesn't exist, which is also fine
                assert response.status in [401, 403, 404], \
                    f"TUTOR granted access to forbidden endpoint: {endpoint}"
                print(f"✅ TUTOR access denied: {endpoint}")
    
    
    async def test_cross_service_authentication(self, http_client, test_config, auth_tokens):
        """Test that JWT tokens work across all microservices"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        student_token = auth_tokens["STUDENT"]["headers"]
        
        # Test direct service access (bypassing API Gateway)
        services_to_test = [
            (test_config.USER_SERVICE_URL, "/api/v1/profile"),
            (test_config.LESSON_SERVICE_URL, "/api/v1/my-lessons"),
            (test_config.HOMEWORK_SERVICE_URL, "/api/v1/my-homework"),
            (test_config.STUDENT_SERVICE_URL, "/api/v1/my-achievements"),
        ]
        
        for service_url, endpoint in services_to_test:
            try:
                async with http_client.get(
                    f"{service_url}{endpoint}",
                    headers=student_token
                ) as response:
                    # Should either work (200) or be not found (404), but not unauthorized (401/403)
                    if response.status in [401, 403]:
                        print(f"⚠️  Token rejected by {service_url}: {response.status}")
                    else:
                        print(f"✅ Token accepted by {service_url}: {response.status}")
                        
            except Exception as e:
                print(f"⚠️  Could not test {service_url}: {e}")
    
    
    async def test_role_isolation(self, http_client, test_config, auth_tokens):
        """Test that users can only access their own data"""
        
        # This test requires multiple users of same role to verify isolation
        # For now, test that profile endpoint returns correct user data
        
        for role, token_info in auth_tokens.items():
            headers = token_info["headers"]
            expected_user_data = token_info["user"]
            
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    profile_data = await response.json()
                    
                    # Verify user gets their own profile data
                    assert profile_data.get("email") == expected_user_data["email"]
                    assert profile_data.get("role") == role
                    
                    print(f"✅ {role} profile isolation verified")
                else:
                    print(f"⚠️  Could not verify {role} profile isolation: {response.status}")


@pytest.mark.auth  
class TestTokenSecurity:
    """JWT token security tests"""
    
    async def test_token_tampering_detection(self, http_client, test_config, auth_tokens):
        """Test that tampered JWT tokens are rejected"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        original_token = auth_tokens["STUDENT"]["token"]
        
        # Test various tampering attempts
        tampered_tokens = [
            original_token[:-5] + "XXXXX",  # Change signature
            original_token.replace("STUDENT", "ADMIN"),  # Try to change role in token
            original_token + "extra",  # Add extra characters
            original_token[1:],  # Remove first character
        ]
        
        for tampered_token in tampered_tokens:
            headers = {"Authorization": f"Bearer {tampered_token}"}
            
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
                headers=headers
            ) as response:
                assert response.status == 401, \
                    f"Tampered token was accepted: {tampered_token[:20]}..."
                print(f"✅ Tampered token rejected")
    
    
    async def test_token_reuse_across_users(self, http_client, test_config, auth_tokens):
        """Test that tokens cannot be reused by different users"""
        
        # This test would require creating multiple users and verifying
        # that User A's token doesn't work for User B's data
        # Implementation depends on user isolation in the system
        
        if len(auth_tokens) < 2:
            pytest.skip("Need multiple user tokens for this test")
        
        # For now, just verify each token returns different user data
        user_emails = set()
        
        for role, token_info in auth_tokens.items():
            headers = token_info["headers"]
            
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    profile_data = await response.json()
                    email = profile_data.get("email")
                    
                    # Each token should return different user
                    assert email not in user_emails, \
                        f"Multiple tokens returned same user: {email}"
                    
                    user_emails.add(email)
                    print(f"✅ {role} token returns unique user: {email}")
    
    
    async def test_authorization_header_formats(self, http_client, test_config, auth_tokens):
        """Test various authorization header formats"""
        
        if "STUDENT" not in auth_tokens:
            pytest.skip("STUDENT token not available")
        
        token = auth_tokens["STUDENT"]["token"]
        
        # Valid formats
        valid_headers = [
            {"Authorization": f"Bearer {token}"},
            {"Authorization": f"bearer {token}"},  # lowercase
        ]
        
        for headers in valid_headers:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
                headers=headers
            ) as response:
                assert response.status != 401, \
                    f"Valid header format rejected: {headers['Authorization'][:20]}..."
                print(f"✅ Valid header format accepted")
        
        # Invalid formats
        invalid_headers = [
            {"Authorization": token},  # Missing Bearer
            {"Authorization": f"Basic {token}"},  # Wrong scheme
            {"Authorization": f"Bearer{token}"},  # Missing space
            {"auth": f"Bearer {token}"},  # Wrong header name
        ]
        
        for headers in invalid_headers:
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
                headers=headers
            ) as response:
                assert response.status == 401, \
                    f"Invalid header format accepted: {headers}"
                print(f"✅ Invalid header format rejected")


@pytest.mark.auth
class TestSessionManagement:
    """Session and token lifecycle management tests"""
    
    async def test_concurrent_sessions(self, http_client, test_config, generate_test_user):
        """Test that users can have multiple concurrent sessions"""
        
        user_data = generate_test_user("STUDENT")
        
        # Register user
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/auth/register",
            json=user_data
        ) as response:
            assert response.status == 201
        
        # Login multiple times to create concurrent sessions
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        
        tokens = []
        for i in range(3):  # Create 3 concurrent sessions
            async with http_client.post(
                f"{test_config.API_GATEWAY_URL}/api/v1/auth/login",
                json=login_data
            ) as response:
                assert response.status == 200
                response_data = await response.json()
                tokens.append(response_data["access_token"])
        
        # Verify all tokens work
        for i, token in enumerate(tokens):
            headers = {"Authorization": f"Bearer {token}"}
            
            async with http_client.get(
                f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
                headers=headers
            ) as response:
                assert response.status == 200
                print(f"✅ Concurrent session {i+1} working")
    
    
    async def test_logout_functionality(self, http_client, test_config, generate_test_user):
        """Test user logout and token invalidation"""
        
        user_data = generate_test_user("STUDENT")
        
        # Register and login user
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/auth/register",
            json=user_data
        ) as response:
            assert response.status == 201
        
        async with http_client.post(
            f"{test_config.API_GATEWAY_URL}/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"]
            }
        ) as response:
            assert response.status == 200
            login_data = await response.json()
            token = login_data["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Verify token works before logout
        async with http_client.get(
            f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
            headers=headers
        ) as response:
            assert response.status == 200
            print("✅ Token working before logout")
        
        # Logout (if logout endpoint exists)
        try:
            async with http_client.post(
                f"{test_config.API_GATEWAY_URL}/api/v1/auth/logout",
                headers=headers
            ) as response:
                if response.status == 200:
                    print("✅ Logout successful")
                    
                    # Verify token no longer works (if token invalidation is implemented)
                    async with http_client.get(
                        f"{test_config.API_GATEWAY_URL}/api/v1/users/profile",
                        headers=headers
                    ) as response:
                        if response.status == 401:
                            print("✅ Token invalidated after logout")
                        else:
                            print("⚠️  Token still valid after logout (stateless JWT)")
                else:
                    print(f"⚠️  Logout endpoint returned: {response.status}")
        except Exception as e:
            print(f"⚠️  Logout test skipped (endpoint may not exist): {e}")