import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def admin_user():
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
        is_admin=True,
    )


@pytest.mark.django_db
class TestLoginView:
    def test_login_success(self, api_client, user):
        url = reverse("login")
        data = {"login": "testuser", "password": "testpass123"}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user_type"] == "custom_user"

    def test_login_invalid_credentials(self, api_client):
        """Invalid credentials return 403 (AuthenticationFailed)."""
        url = reverse("login")
        data = {"login": "invalid", "password": "invalid"}
        response = api_client.post(url, data)

        # AuthenticationFailed returns 403
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_login_missing_fields(self, api_client):
        """Missing fields return 400 (ValidationError)."""
        url = reverse("login")
        data = {"login": "testuser"}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogoutView:
    def test_logout_success(self, api_client, user):
        # First login to get tokens
        login_url = reverse("login")
        login_data = {"login": "testuser", "password": "testpass123"}
        login_response = api_client.post(login_url, login_data)

        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # Now logout
        logout_url = reverse("logout")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_data = {"refresh": refresh_token}
        response = api_client.post(logout_url, logout_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Successfully logged out"

    def test_logout_unauthenticated(self, api_client):
        """Unauthenticated requests return 403 (PermissionDenied)."""
        url = reverse("logout")
        response = api_client.post(url, {})

        # REST_FRAMEWORK default permission class returns 403 for unauthenticated
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestProfileView:
    def test_profile_success(self, api_client, user):
        # Login first
        login_url = reverse("login")
        login_data = {"login": "testuser", "password": "testpass123"}
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data["access"]

        # Get profile
        profile_url = reverse("profile")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get(profile_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"
        assert response.data["email"] == "test@example.com"
        # Test that user has timestamp fields from TimestampedModel
        assert hasattr(user, "created_at")
        assert hasattr(user, "updated_at")

    def test_profile_unauthenticated(self, api_client):
        """Unauthenticated requests return 403 (PermissionDenied)."""
        url = reverse("profile")
        response = api_client.get(url)

        # REST_FRAMEWORK default permission class returns 403 for unauthenticated
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestRegisterView:
    def test_register_success_admin(self, api_client, admin_user):
        # Login as admin
        login_url = reverse("login")
        login_data = {"login": "admin", "password": "adminpass123"}
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data["access"]

        # Register new user
        register_url = reverse("register")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        register_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
            "first_name": "New",
            "last_name": "User",
        }
        response = api_client.post(register_url, register_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "newuser"
        assert User.objects.filter(username="newuser").exists()

    def test_register_non_admin_forbidden(self, api_client, user):
        # Login as regular user
        login_url = reverse("login")
        login_data = {"login": "testuser", "password": "testpass123"}
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data["access"]

        # Try to register new user
        register_url = reverse("register")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        register_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
        }
        response = api_client.post(register_url, register_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_register_password_mismatch(self, api_client, admin_user):
        # Login as admin
        login_url = reverse("login")
        login_data = {"login": "admin", "password": "adminpass123"}
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data["access"]

        # Try to register with mismatched passwords
        register_url = reverse("register")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        register_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
            "password_confirm": "differentpass",
        }
        response = api_client.post(register_url, register_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUnifiedManagerLogin:
    """Test unified login for Manager users with phone + password"""

    def test_manager_login_with_phone_and_password(self, api_client):
        """Test that manager can login with phone + password"""
        from apps.accounts.models import CustomUser

        # Create a manager with password
        manager = CustomUser.objects.create(
            first_name="John",
            phone_number="+998901234567",
            username="mgr_+998901234567",
            user_type="manager",
        )
        manager.set_password("managerpass123")
        manager.save()

        # Login with phone + password
        url = reverse("login")
        data = {"login": "+998901234567", "password": "managerpass123"}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_type"] == "manager"
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["id"] == manager.id
        assert response.data["user"]["phone_number"] == "+998901234567"

    def test_manager_login_invalid_password(self, api_client):
        """Test that manager cannot login with wrong password"""
        from apps.accounts.models import CustomUser

        manager = CustomUser.objects.create(
            first_name="John",
            phone_number="+998901234568",
            username="mgr_+998901234568",
            user_type="manager",
        )
        manager.set_password("correctpass123")
        manager.save()

        url = reverse("login")
        data = {"login": "+998901234568", "password": "wrongpass123"}
        response = api_client.post(url, data)

        # AuthenticationFailed returns 403
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_manager_login_nonexistent_phone(self, api_client):
        """Test that login fails for nonexistent phone"""
        url = reverse("login")
        data = {"login": "+998999999999", "password": "anypass123"}
        response = api_client.post(url, data)

        # AuthenticationFailed returns 403
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_manager_login_deactivated(self, api_client):
        """Test that deactivated manager cannot login"""
        from apps.accounts.models import CustomUser

        manager = CustomUser.objects.create(
            first_name="John",
            phone_number="+998901234569",
            is_active=False,
            username="mgr_+998901234569",
            user_type="manager",
        )
        manager.set_password("pass123")
        manager.save()

        url = reverse("login")
        data = {"login": "+998901234569", "password": "pass123"}
        response = api_client.post(url, data)

        # AuthenticationFailed or PermissionDenied
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]
        assert response.data["success"] is False

    def test_unified_login_detects_phone_vs_username(self, api_client):
        """Test that unified login correctly detects phone vs username"""
        from apps.accounts.models import CustomUser

        # Create a manager
        manager = CustomUser.objects.create(
            first_name="Manager",
            phone_number="+998901234570",
            username="mgr_+998901234570",
            user_type="manager",
        )
        manager.set_password("pass123")
        manager.save()

        # Create a user with username 'user'
        user = User.objects.create_user(username="user", password="pass123")

        # Login with phone - should return manager
        url = reverse("login")
        phone_data = {"login": "+998901234570", "password": "pass123"}
        phone_response = api_client.post(url, phone_data)

        assert phone_response.status_code == status.HTTP_200_OK
        assert phone_response.data["user_type"] == "manager"
        assert phone_response.data["user"]["id"] == manager.id

        # Login with username - should return custom_user
        username_data = {"login": "user", "password": "pass123"}
        username_response = api_client.post(url, username_data)

        assert username_response.status_code == status.HTTP_200_OK
        assert username_response.data["user_type"] == "custom_user"
        assert username_response.data["user"]["id"] == user.id
