"""
Simplified tests for Manager access control system.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.accounts.services import ManagerService


User = get_user_model()


@pytest.mark.django_db
class TestManagerModel:
    """Test Manager model properties and validation."""

    def test_manager_creation(self):
        """Test creating a manager with valid data."""
        manager = CustomUser.objects.create(
            first_name='Test',
            phone_number='+998901234567',
            username='mgr_+998901234567',
            user_type='manager'
        )
        assert manager.id is not None
        assert manager.first_name == 'Test'
        assert manager.is_active is True
        assert manager.bot_access is False

    def test_can_use_bot(self):
        """Test can_use_bot property."""
        manager = CustomUser.objects.create(
            first_name='Test',
            phone_number='+998901234570',
            telegram_user_id=123456789,
            bot_access=True,
            is_active=True,
            username='mgr_+998901234570',
            user_type='manager'
        )
        assert manager.can_use_bot is True

        # Test deactivated
        manager.is_active = False
        assert manager.can_use_bot is False

        # Test no access
        manager.is_active = True
        manager.bot_access = False
        assert manager.can_use_bot is False

        # Test no telegram
        manager.bot_access = True
        manager.telegram_user_id = None
        assert manager.can_use_bot is False


@pytest.mark.django_db
class TestManagerService:
    """Test ManagerService business logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ManagerService()

    def test_validate_phone_number(self):
        """Test phone number validation."""
        # Valid formats
        assert self.service.validate_phone_number('+998901234567') == '+998901234567'
        assert self.service.validate_phone_number('998901234567') == '+998901234567'

    def test_create_manager(self):
        """Test creating a manager."""
        manager = self.service.create_manager(
            phone_number='+998901234572',
            first_name='Test'
        )
        assert manager.id is not None
        assert manager.phone_number == '+998901234572'
        assert manager.first_name == 'Test'

    def test_activate_telegram_user(self):
        """Test linking Telegram account."""
        manager = self.service.create_manager(
            phone_number='+998901234574',
            first_name='Test'
        )

        result_manager, status = self.service.activate_telegram_user(
            phone_number='+998901234574',
            telegram_user_id=123456789,
            telegram_username='test_user'
        )

        assert result_manager.telegram_user_id == 123456789
        assert result_manager.telegram_username == 'test_user'
        assert status['already_linked'] is False
        assert status['has_access'] is False


@pytest.mark.django_db
class TestManagerAPI:
    """Test Manager API endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.admin = User.objects.create_user(
            username='api_admin',
            password='testpass',
            is_admin=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_list_managers(self):
        """Test listing managers."""
        CustomUser.objects.create(
            first_name='Test1',
            phone_number='+998901234581',
            username='mgr_+998901234581',
            user_type='manager'
        )
        CustomUser.objects.create(
            first_name='Test2',
            phone_number='+998901234582',
            username='mgr_+998901234582',
            user_type='manager'
        )

        response = self.client.get('/api/auth/managers/')
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_create_manager_via_api(self):
        """Test creating manager via API."""
        data = {
            'first_name': 'API',
            'phone_number': '+998901234583'
        }

        response = self.client.post('/api/auth/managers/', data)
        assert response.status_code == 201
        # Response has nested data structure
        assert response.data['success'] is True
        assert 'id' in response.data['data']

    def test_grant_access_via_api(self):
        """Test granting access via API."""
        manager = CustomUser.objects.create(
            first_name='Test',
            phone_number='+998901234584',
            username='mgr_+998901234584',
            user_type='manager'
        )

        response = self.client.post(f'/api/auth/managers/{manager.id}/grant-access/')
        assert response.status_code == 200
        assert response.data['success'] is True

        manager.refresh_from_db()
        assert manager.bot_access is True

    def test_revoke_access_via_api(self):
        """Test revoking access via API."""
        manager = CustomUser.objects.create(
            first_name='Test',
            phone_number='+998901234585',
            bot_access=True,
            username='mgr_+998901234585',
            user_type='manager'
        )

        response = self.client.post(f'/api/auth/managers/{manager.id}/revoke-access/')
        assert response.status_code == 200
        assert response.data['success'] is True

        manager.refresh_from_db()
        assert manager.bot_access is False


@pytest.mark.django_db
class TestManagerIntegration:
    """Integration tests for complete Manager workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ManagerService()

    def test_complete_manager_lifecycle(self):
        """Test complete manager lifecycle from creation to access grant."""
        # Step 1: Admin creates manager
        manager = self.service.create_manager(
            phone_number='+998901234588',
            first_name='Integration'
        )
        assert manager.id is not None
        assert manager.bot_access is False

        # Step 2: Manager starts bot and shares phone
        manager, status = self.service.activate_telegram_user(
            phone_number='+998901234588',
            telegram_user_id=999888777,
            telegram_username='integration_test'
        )
        assert manager.telegram_user_id == 999888777
        assert status['has_access'] is False

        # Step 3: Admin grants access directly
        manager.bot_access = True
        manager.save()
        manager.refresh_from_db()
        assert manager.can_use_bot is True

        # Step 4: Manager can now create entries
        assert manager.is_active is True
        assert manager.telegram_user_id is not None


@pytest.mark.django_db
class TestManagerPassword:
    """Test manager password creation and updates."""

    def setup_method(self):
        """Create an admin user for API tests."""
        self.admin = User.objects.create_user(
            username='admin',
            password='adminpass123',
            is_admin=True
        )
        self.client = APIClient()
        # Login as admin
        response = self.client.post('/api/auth/login/', {
            'login': 'admin',
            'password': 'adminpass123'
        })
        self.admin_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

    def test_create_manager_with_password_via_api(self):
        """Test creating manager with password via API."""
        data = {
            'first_name': 'PasswordTest',
            'phone_number': '+998901234590',
            'password': 'securepass123'
        }

        response = self.client.post('/api/auth/managers/', data)
        assert response.status_code == 201
        # Response has nested data structure
        assert response.data['success'] is True
        assert 'id' in response.data['data']

        # Verify password was saved by attempting login
        manager = CustomUser.objects.get(id=response.data['data']['id'])
        assert manager.check_password('securepass123') is True

    def test_manager_password_login_after_creation(self):
        """Test that manager can login with password after creation."""
        # Create manager with password via service
        service = ManagerService()
        manager = service.create_manager(
            phone_number='+998901234591',
            first_name='LoginTest',
            password='testpass456'
        )

        # Logout as admin
        self.client.post('/api/auth/logout/', {'refresh': 'dummy'})
        self.client.credentials()

        # Login as manager with phone + password
        response = self.client.post('/api/auth/login/', {
            'login': '+998901234591',
            'password': 'testpass456'
        })

        assert response.status_code == 200
        assert response.data['user_type'] == 'manager'
        assert response.data['user']['id'] == manager.id

    def test_update_manager_password_via_api(self):
        """Test updating manager password via API."""
        # Create manager
        manager = CustomUser.objects.create(
            first_name='UpdateTest',
            phone_number='+998901234592',
            username='mgr_+998901234592',
            user_type='manager'
        )
        manager.set_password('oldpass123')
        manager.save()

        # Update with new password
        data = {
            'first_name': 'UpdateTest',
            'phone_number': '+998901234592',
            'password': 'newpass456'
        }

        response = self.client.patch(f'/api/auth/managers/{manager.id}/', data)
        assert response.status_code == 200

        # Verify new password works
        manager.refresh_from_db()
        assert manager.check_password('newpass456') is True
        assert manager.check_password('oldpass123') is False

    def test_manager_can_access_profile_endpoint(self):
        """Test that manager can access profile endpoint after login."""
        # Create manager with password
        service = ManagerService()
        manager = service.create_manager(
            phone_number='+998901234593',
            first_name='ProfileTest',
            password='profilepass123'
        )

        # Logout as admin
        self.client.post('/api/auth/logout/', {'refresh': 'dummy'})
        self.client.credentials()

        # Login as manager
        response = self.client.post('/api/auth/login/', {
            'login': '+998901234593',
            'password': 'profilepass123'
        })
        assert response.status_code == 200
        manager_token = response.data['access']

        # Access profile endpoint as manager
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {manager_token}')
        profile_response = self.client.get('/api/auth/profile/')

        assert profile_response.status_code == 200
        assert profile_response.data['first_name'] == 'ProfileTest'
        assert profile_response.data['phone_number'] == '+998901234593'
        assert profile_response.data['id'] == manager.id


@pytest.mark.django_db
class TestManagerSelfProfile:
    """Test manager self-profile endpoint (manager page showing only themselves)."""

    def setup_method(self):
        """Create managers and authenticated client."""
        self.client = APIClient()

        # Create manager 1
        self.service = ManagerService()
        self.manager1 = self.service.create_manager(
            phone_number='+998901234600',
            first_name='Manager1',
            password='pass123'
        )

        # Create manager 2
        self.manager2 = self.service.create_manager(
            phone_number='+998901234601',
            first_name='Manager2',
            password='pass123'
        )

    def test_manager_can_access_own_profile(self):
        """Test manager can view their own profile via /manager/profile/."""
        # Login as manager1
        response = self.client.post('/api/auth/login/', {
            'login': '+998901234600',
            'password': 'pass123'
        })
        token = response.data['access']

        # Access manager profile endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        profile_response = self.client.get('/api/auth/manager/profile/')

        assert profile_response.status_code == 200
        assert profile_response.data['id'] == self.manager1.id
        assert profile_response.data['first_name'] == 'Manager1'
        assert profile_response.data['phone_number'] == '+998901234600'

    def test_manager_only_sees_their_own_data(self):
        """Test manager cannot see other managers' data."""
        # Login as manager1
        response = self.client.post('/api/auth/login/', {
            'login': '+998901234600',
            'password': 'pass123'
        })
        token = response.data['access']

        # Access manager profile endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        profile_response = self.client.get('/api/auth/manager/profile/')

        # Should only see manager1's data, not manager2
        assert profile_response.data['id'] == self.manager1.id
        assert profile_response.data['first_name'] == 'Manager1'
        assert profile_response.data['first_name'] != 'Manager2'

    def test_manager_can_update_own_profile(self):
        """Test manager can update their own profile."""
        # Login as manager1
        response = self.client.post('/api/auth/login/', {
            'login': '+998901234600',
            'password': 'pass123'
        })
        token = response.data['access']

        # Update own profile
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        update_response = self.client.patch('/api/auth/manager/profile/', {
            'first_name': 'UpdatedManager1'
        })

        assert update_response.status_code == 200
        assert update_response.data['first_name'] == 'UpdatedManager1'

        # Verify update persisted
        self.manager1.refresh_from_db()
        assert self.manager1.first_name == 'UpdatedManager1'

    def test_manager_can_update_password_via_profile(self):
        """Test manager can update their own password via profile endpoint."""
        # Login as manager1
        response = self.client.post('/api/auth/login/', {
            'login': '+998901234600',
            'password': 'pass123'
        })
        token = response.data['access']

        # Update password
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        update_response = self.client.patch('/api/auth/manager/profile/', {
            'password': 'newpass456'
        })

        assert update_response.status_code == 200

        # Verify old password doesn't work anymore
        self.client.credentials()
        login_response = self.client.post('/api/auth/login/', {
            'login': '+998901234600',
            'password': 'pass123'
        })
        # AuthenticationFailed returns 403
        assert login_response.status_code == 403

        # Verify new password works
        login_response = self.client.post('/api/auth/login/', {
            'login': '+998901234600',
            'password': 'newpass456'
        })
        assert login_response.status_code == 200

    def test_non_manager_cannot_access_manager_profile(self):
        """Test that non-manager users (CustomUser) cannot access /manager/profile/."""
        # Create admin user
        admin = User.objects.create_user(
            username='admin',
            password='adminpass',
            is_admin=True
        )

        # Login as admin
        response = self.client.post('/api/auth/login/', {
            'login': 'admin',
            'password': 'adminpass'
        })
        token = response.data['access']

        # Try to access manager profile endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        profile_response = self.client.get('/api/auth/manager/profile/')

        assert profile_response.status_code == 403
        assert 'Only managers can access' in str(profile_response.data)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
