"""
Test script to verify login validation errors are properly centralized.

Run with: python manage.py shell < test_login_validation.py
Or: python manage.py shell
    >>> exec(open('test_login_validation.py').read())
"""

import json

from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser


# Create test client
client = APIClient()

# Setup test data
print("=" * 80)
print("SETTING UP TEST DATA")
print("=" * 80)

# Create active user
active_user, created = CustomUser.objects.get_or_create(
    username="testuser",
    defaults={
        "email": "test@example.com",
        "password": make_password("testpass123"),
        "is_active": True,
        "user_type": "api_user",
    },
)
if created:
    print("✓ Created active user: testuser / testpass123")
else:
    print("✓ Using existing active user: testuser")

# Create inactive user
inactive_user, created = CustomUser.objects.get_or_create(
    username="inactiveuser",
    defaults={
        "email": "inactive@example.com",
        "password": make_password("testpass123"),
        "is_active": False,
        "user_type": "api_user",
    },
)
if created:
    print("✓ Created inactive user: inactiveuser / testpass123")
else:
    print("✓ Using existing inactive user: inactiveuser")

# Create active manager
try:
    manager = CustomUser.objects.get(phone_number="+998901234567")
    manager.is_active = True
    manager.set_password("managerpass123")
    manager.save()
    print("✓ Using existing active manager: +998901234567 / managerpass123")
except CustomUser.DoesNotExist:
    manager = CustomUser.objects.create(
        username="mgr_+998901234567",
        phone_number="+998901234567",
        first_name="Test Manager",
        password=make_password("managerpass123"),
        is_active=True,
        user_type="manager",
    )
    print("✓ Created active manager: +998901234567 / managerpass123")

# Create inactive manager
try:
    inactive_manager = CustomUser.objects.get(phone_number="+998909999999")
    inactive_manager.is_active = False
    inactive_manager.set_password("managerpass123")
    inactive_manager.save()
    print("✓ Using existing inactive manager: +998909999999 / managerpass123")
except CustomUser.DoesNotExist:
    inactive_manager = CustomUser.objects.create(
        username="mgr_+998909999999",
        phone_number="+998909999999",
        first_name="Inactive Manager",
        password=make_password("managerpass123"),
        is_active=False,
        user_type="manager",
    )
    print("✓ Created inactive manager: +998909999999 / managerpass123")

print("\n")


# Test scenarios
def print_response(title, response):
    """Helper to print formatted response"""
    print("-" * 80)
    print(f"TEST: {title}")
    print("-" * 80)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print()


# Test 1: Missing credentials
print("=" * 80)
print("TEST 1: MISSING CREDENTIALS (ValidationError)")
print("=" * 80)
response = client.post("/api/auth/login/", {"login": "", "password": ""}, format="json")
print_response("Empty login and password", response)

# Test 2: Wrong username
print("=" * 80)
print("TEST 2: WRONG USERNAME (AuthenticationFailed)")
print("=" * 80)
response = client.post(
    "/api/auth/login/",
    {"login": "wronguser", "password": "somepassword"},
    format="json",
)
print_response("Non-existent username", response)

# Test 3: Wrong password
print("=" * 80)
print("TEST 3: WRONG PASSWORD (AuthenticationFailed)")
print("=" * 80)
response = client.post(
    "/api/auth/login/",
    {"login": "testuser", "password": "wrongpassword"},
    format="json",
)
print_response("Existing user with wrong password", response)

# Test 4: Inactive user account
print("=" * 80)
print("TEST 4: INACTIVE USER ACCOUNT (PermissionDenied)")
print("=" * 80)
response = client.post(
    "/api/auth/login/",
    {"login": "inactiveuser", "password": "testpass123"},
    format="json",
)
print_response("Inactive user with correct password", response)

# Test 5: Successful login
print("=" * 80)
print("TEST 5: SUCCESSFUL LOGIN (Active User)")
print("=" * 80)
response = client.post(
    "/api/auth/login/", {"login": "testuser", "password": "testpass123"}, format="json"
)
print_response("Active user with correct credentials", response)

# Test 6: Wrong phone number (manager)
print("=" * 80)
print("TEST 6: WRONG PHONE NUMBER (AuthenticationFailed)")
print("=" * 80)
response = client.post(
    "/api/auth/login/",
    {"login": "+998999999999", "password": "somepassword"},
    format="json",
)
print_response("Non-existent phone number", response)

# Test 7: Wrong manager password
print("=" * 80)
print("TEST 7: WRONG MANAGER PASSWORD (AuthenticationFailed)")
print("=" * 80)
response = client.post(
    "/api/auth/login/",
    {"login": "+998901234567", "password": "wrongpassword"},
    format="json",
)
print_response("Existing manager with wrong password", response)

# Test 8: Inactive manager account
print("=" * 80)
print("TEST 8: INACTIVE MANAGER ACCOUNT (PermissionDenied)")
print("=" * 80)
response = client.post(
    "/api/auth/login/",
    {"login": "+998909999999", "password": "managerpass123"},
    format="json",
)
print_response("Inactive manager with correct password", response)

# Test 9: Successful manager login
print("=" * 80)
print("TEST 9: SUCCESSFUL MANAGER LOGIN (Active Manager)")
print("=" * 80)
response = client.post(
    "/api/auth/login/",
    {"login": "+998901234567", "password": "managerpass123"},
    format="json",
)
print_response("Active manager with correct credentials", response)

# Summary
print("=" * 80)
print("SUMMARY - ERROR CODES VERIFICATION")
print("=" * 80)
print("✓ VALIDATION_ERROR      → Missing/empty credentials")
print("✓ AUTHENTICATION_FAILED → Wrong username/phone/password")
print("✓ PERMISSION_DENIED     → Inactive account (correct credentials)")
print("=" * 80)
print("\nAll tests completed! Check responses above.")
print("=" * 80)
