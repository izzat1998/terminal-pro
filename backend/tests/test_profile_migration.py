"""
Tests for profile migration from legacy CustomUser fields to Profile models.
Ensures backward compatibility during the migration period.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Company, CustomerProfile, ManagerProfile

User = get_user_model()


@pytest.mark.django_db
class TestManagerProfileMigration:
    """Test manager profile migration and usage."""

    def test_manager_profile_created_on_user_creation(self):
        """New managers should get profiles automatically via serializer."""
        from apps.accounts.serializers import ManagerCreateSerializer

        data = {
            "first_name": "Test Manager",
            "phone_number": "+998991234567",
            "password": "testpass123",
            "bot_access": True,
            "gate_access": True,
            "is_active": True,
        }
        serializer = ManagerCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        manager = serializer.save()

        # Should have profile
        assert manager.has_profile()
        profile = manager.get_profile()
        assert isinstance(profile, ManagerProfile)
        assert profile.phone_number == "+998991234567"
        assert profile.bot_access is True
        assert profile.gate_access is True

    def test_manager_profile_updated_on_user_update(self):
        """Updating a manager should update their profile."""
        from apps.accounts.serializers import ManagerCreateSerializer, ManagerUpdateSerializer

        # Create manager
        create_data = {
            "first_name": "Original Name",
            "phone_number": "+998991234567",
            "password": "testpass123",
            "bot_access": False,
            "gate_access": False,
            "is_active": True,
        }
        serializer = ManagerCreateSerializer(data=create_data)
        assert serializer.is_valid()
        manager = serializer.save()

        # Update manager
        update_data = {
            "first_name": "Updated Name",
            "phone_number": "+998999999999",
            "bot_access": True,
            "gate_access": True,
            "is_active": True,
        }
        serializer = ManagerUpdateSerializer(manager, data=update_data)
        assert serializer.is_valid(), serializer.errors
        updated_manager = serializer.save()

        # Check profile was updated
        profile = updated_manager.get_profile()
        assert profile.phone_number == "+998999999999"
        assert profile.bot_access is True
        assert profile.gate_access is True

    def test_manager_authentication_via_profile(self):
        """Managers should be able to authenticate using profile phone number."""
        from apps.accounts.serializers import ManagerCreateSerializer, UnifiedLoginSerializer

        # Create manager
        create_data = {
            "first_name": "Auth Test",
            "phone_number": "+998991234567",
            "password": "testpass123",
            "bot_access": True,
            "gate_access": True,
            "is_active": True,
        }
        serializer = ManagerCreateSerializer(data=create_data)
        assert serializer.is_valid()
        manager = serializer.save()

        # Authenticate with phone from profile
        login_data = {
            "login": "+998991234567",
            "password": "testpass123",
        }
        serializer = UnifiedLoginSerializer(data=login_data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["user"] == manager
        assert serializer.validated_data["user_type"] == "manager"

    def test_manager_serializer_reads_from_profile(self):
        """ManagerSerializer should read from profile when available."""
        from apps.accounts.serializers import ManagerCreateSerializer, ManagerSerializer

        # Create manager
        create_data = {
            "first_name": "Profile Test",
            "phone_number": "+998991234567",
            "password": "testpass123",
            "bot_access": True,
            "gate_access": True,
            "is_active": True,
        }
        serializer = ManagerCreateSerializer(data=create_data)
        assert serializer.is_valid()
        manager = serializer.save()

        # Serialize manager
        serializer = ManagerSerializer(manager)
        data = serializer.data

        # Should read from profile
        assert data["phone_number"] == "+998991234567"
        assert data["bot_access"] is True
        assert data["gate_access"] is True
        assert data["has_profile"] is True


@pytest.mark.django_db
class TestCustomerProfileMigration:
    """Test customer profile migration and usage."""

    def test_customer_profile_created_on_user_creation(self):
        """New customers should get profiles automatically via serializer."""
        from apps.accounts.serializers import CustomerCreateSerializer

        # Create company first
        company = Company.objects.create(name="Test Company")

        data = {
            "first_name": "Test Customer",
            "phone_number": "+998991234567",
            "company_id": company.id,
            "bot_access": True,
            "is_active": True,
        }
        serializer = CustomerCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        customer = serializer.save()

        # Should have profile
        assert customer.has_profile()
        profile = customer.get_profile()
        assert isinstance(profile, CustomerProfile)
        assert profile.phone_number == "+998991234567"
        assert profile.bot_access is True
        assert profile.company == company

    def test_customer_profile_updated_on_user_update(self):
        """Updating a customer should update their profile."""
        from apps.accounts.serializers import CustomerCreateSerializer, CustomerUpdateSerializer

        # Create company
        company = Company.objects.create(name="Test Company")

        # Create customer
        create_data = {
            "first_name": "Original Name",
            "phone_number": "+998991234567",
            "company_id": company.id,
            "bot_access": False,
            "is_active": True,
        }
        serializer = CustomerCreateSerializer(data=create_data)
        assert serializer.is_valid()
        customer = serializer.save()

        # Update customer
        update_data = {
            "first_name": "Updated Name",
            "phone_number": "+998999999999",
            "company_id": company.id,
            "bot_access": True,
            "is_active": True,
        }
        serializer = CustomerUpdateSerializer(customer, data=update_data)
        assert serializer.is_valid(), serializer.errors
        updated_customer = serializer.save()

        # Check profile was updated
        profile = updated_customer.get_profile()
        assert profile.phone_number == "+998999999999"
        assert profile.bot_access is True

    def test_customer_serializer_reads_from_profile(self):
        """CustomerSerializer should read from profile when available."""
        from apps.accounts.serializers import CustomerCreateSerializer, CustomerSerializer

        # Create company
        company = Company.objects.create(name="Test Company")

        # Create customer
        create_data = {
            "first_name": "Profile Test",
            "phone_number": "+998991234567",
            "company_id": company.id,
            "bot_access": True,
            "is_active": True,
        }
        serializer = CustomerCreateSerializer(data=create_data)
        assert serializer.is_valid()
        customer = serializer.save()

        # Serialize customer
        serializer = CustomerSerializer(customer)
        data = serializer.data

        # Should read from profile
        assert data["phone_number"] == "+998991234567"
        assert data["bot_access"] is True
        assert data["has_profile"] is True
        assert data["company"]["id"] == company.id


@pytest.mark.django_db
class TestProfileFallbackBehavior:
    """Test that legacy fields still work as fallback when profile doesn't exist."""

    def test_legacy_manager_without_profile_still_works(self):
        """Legacy managers without profiles should still work via legacy fields."""
        # Create manager directly (bypassing serializer to simulate legacy data)
        manager = User.objects.create_user(
            username="legacy_manager",
            password="testpass123",
            user_type="manager",
            phone_number="+998991234567",
            bot_access=True,
        )

        # Delete profile if it exists (simulate legacy user)
        ManagerProfile.objects.filter(user=manager).delete()

        # Should not have profile
        assert not manager.has_profile()

        # But should still work via profile_* properties
        assert manager.profile_phone_number == "+998991234567"
        assert manager.profile_bot_access is True

    def test_legacy_customer_without_profile_still_works(self):
        """Legacy customers without profiles should still work via legacy fields."""
        company = Company.objects.create(name="Test Company")

        # Create customer directly (bypassing serializer to simulate legacy data)
        customer = User.objects.create_user(
            username="legacy_customer",
            password="testpass123",
            user_type="customer",
            phone_number="+998991234567",
            bot_access=True,
            company=company,
        )

        # Delete profile if it exists (simulate legacy user)
        CustomerProfile.objects.filter(user=customer).delete()

        # Should not have profile
        assert not customer.has_profile()

        # But should still work via profile_* properties
        assert customer.profile_phone_number == "+998991234567"
        assert customer.profile_bot_access is True
        assert customer.profile_company == company


@pytest.mark.django_db
class TestPhoneNumberUniqueness:
    """Test phone number uniqueness across profiles and legacy fields."""

    def test_manager_phone_unique_across_profiles(self):
        """Manager phone numbers should be unique in profiles."""
        from apps.accounts.serializers import ManagerCreateSerializer

        # Create first manager
        data1 = {
            "first_name": "Manager 1",
            "phone_number": "+998991234567",
            "password": "testpass123",
            "bot_access": True,
            "gate_access": True,
            "is_active": True,
        }
        serializer = ManagerCreateSerializer(data=data1)
        assert serializer.is_valid()
        serializer.save()

        # Try to create second manager with same phone
        data2 = {
            "first_name": "Manager 2",
            "phone_number": "+998991234567",  # Same phone
            "password": "testpass123",
            "bot_access": True,
            "gate_access": True,
            "is_active": True,
        }
        serializer = ManagerCreateSerializer(data=data2)
        assert not serializer.is_valid()
        # Phone number validation should catch this
        assert "phone_number" in serializer.errors or "non_field_errors" in serializer.errors

    def test_customer_phone_unique_across_profiles(self):
        """Customer phone numbers should be unique in profiles."""
        from apps.accounts.serializers import CustomerCreateSerializer

        company = Company.objects.create(name="Test Company")

        # Create first customer
        data1 = {
            "first_name": "Customer 1",
            "phone_number": "+998991234567",
            "company_id": company.id,
            "bot_access": True,
            "is_active": True,
        }
        serializer = CustomerCreateSerializer(data=data1)
        assert serializer.is_valid()
        serializer.save()

        # Try to create second customer with same phone
        data2 = {
            "first_name": "Customer 2",
            "phone_number": "+998991234567",  # Same phone
            "company_id": company.id,
            "bot_access": True,
            "is_active": True,
        }
        serializer = CustomerCreateSerializer(data=data2)
        assert not serializer.is_valid()
        # Phone number validation should catch this
        assert "phone_number" in serializer.errors or "non_field_errors" in serializer.errors
