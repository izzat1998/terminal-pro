"""
Tests for customer portal permission classes.
"""

import pytest
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory

from apps.accounts.models import Company, CustomerProfile, CustomUser
from apps.containers.models import Container
from apps.customer_portal.permissions import (
    HasCompanyAccess,
    IsCustomer,
    IsCustomerOwner,
)
from apps.terminal_operations.models import ContainerEntry, PreOrder


@pytest.fixture
def company1(db):
    """Create first test company."""
    return Company.objects.create(name="Company 1", slug="company-1")


@pytest.fixture
def company2(db):
    """Create second test company."""
    return Company.objects.create(name="Company 2", slug="company-2")


@pytest.fixture
def customer_user(db, company1):
    """Create a customer user."""
    user = CustomUser.objects.create_user(
        username="customer1",
        password="password123",
        user_type="customer",
        first_name="Test",
        last_name="Customer",
    )
    CustomerProfile.objects.create(
        user=user, company=company1, phone_number="+998901111111"
    )
    return user


@pytest.fixture
def customer_user2(db, company2):
    """Create a second customer user from different company."""
    user = CustomUser.objects.create_user(
        username="customer2",
        password="password123",
        user_type="customer",
        first_name="Test",
        last_name="Customer2",
    )
    CustomerProfile.objects.create(
        user=user, company=company2, phone_number="+998902222222"
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return CustomUser.objects.create_user(
        username="admin",
        password="password123",
        user_type="admin",
        is_staff=True,
    )


@pytest.fixture
def manager_user(db):
    """Create a manager user."""
    return CustomUser.objects.create_user(
        username="manager",
        password="password123",
        user_type="manager",
        phone_number="+998903333333",
    )


@pytest.fixture
def api_factory():
    """Create API request factory."""
    return APIRequestFactory()


@pytest.mark.django_db
class TestIsCustomerPermission:
    """Tests for IsCustomer permission class."""

    def test_allows_authenticated_customer(self, api_factory, customer_user):
        """Test that IsCustomer allows authenticated customer users."""
        request = api_factory.get("/")
        request.user = customer_user

        permission = IsCustomer()
        assert permission.has_permission(request, None) is True

    def test_denies_admin_user(self, api_factory, admin_user):
        """Test that IsCustomer denies admin users."""
        request = api_factory.get("/")
        request.user = admin_user

        permission = IsCustomer()
        assert permission.has_permission(request, None) is False

    def test_denies_manager_user(self, api_factory, manager_user):
        """Test that IsCustomer denies manager users."""
        request = api_factory.get("/")
        request.user = manager_user

        permission = IsCustomer()
        assert permission.has_permission(request, None) is False

    def test_denies_unauthenticated_user(self, api_factory):
        """Test that IsCustomer denies unauthenticated users."""
        from django.contrib.auth.models import AnonymousUser

        request = api_factory.get("/")
        request.user = AnonymousUser()

        permission = IsCustomer()
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsCustomerOwnerPermission:
    """Tests for IsCustomerOwner permission class."""

    def test_allows_owner_access_to_own_preorder(
        self, api_factory, customer_user, company1
    ):
        """Test that customer can access their own pre-order."""
        request = api_factory.get("/")
        request.user = customer_user

        # Create pre-order owned by customer
        preorder = PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A123BC",
            operation_type="LOAD",
        )

        permission = IsCustomerOwner()
        assert permission.has_object_permission(request, None, preorder) is True

    def test_denies_access_to_other_customer_preorder(
        self, api_factory, customer_user, customer_user2
    ):
        """Test that customer cannot access another customer's pre-order."""
        request = api_factory.get("/")
        request.user = customer_user

        # Create pre-order owned by different customer
        preorder = PreOrder.objects.create(
            customer=customer_user2,
            plate_number="01A123BC",
            operation_type="LOAD",
        )

        permission = IsCustomerOwner()
        assert permission.has_object_permission(request, None, preorder) is False


@pytest.mark.django_db
class TestHasCompanyAccessPermission:
    """Tests for HasCompanyAccess permission class."""

    def test_allows_access_to_own_company_container(
        self, api_factory, customer_user, company1
    ):
        """Test that customer can access their company's containers."""
        request = api_factory.get("/")
        request.user = customer_user

        # Create container for customer's company
        container = Container.objects.create(container_number="HDMU6565958", iso_type="22G1")
        container_entry = ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="01A123BC",
            company=company1,
            recorded_by=customer_user,
        )

        permission = HasCompanyAccess()
        assert permission.has_object_permission(request, None, container_entry) is True

    def test_denies_access_to_other_company_container(
        self, api_factory, customer_user, company2
    ):
        """Test that customer cannot access other company's containers."""
        request = api_factory.get("/")
        request.user = customer_user

        # Create container for different company
        container = Container.objects.create(container_number="HDMU6565959", iso_type="22G1")
        container_entry = ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="01A123BC",
            company=company2,
            recorded_by=customer_user,
        )

        permission = HasCompanyAccess()
        assert permission.has_object_permission(request, None, container_entry) is False

    def test_denies_unauthenticated_access(self, api_factory, company1):
        """Test that unauthenticated users are denied."""
        from django.contrib.auth.models import AnonymousUser

        request = api_factory.get("/")
        request.user = AnonymousUser()

        container = Container.objects.create(container_number="HDMU6565960", iso_type="22G1")
        container_entry = ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="01A123BC",
            company=company1,
        )

        permission = HasCompanyAccess()
        assert permission.has_object_permission(request, None, container_entry) is False
