"""
Integration tests for customer portal API endpoints.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Company, CustomerProfile, CustomUser
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, PreOrder


@pytest.fixture
def company1(db):
    """Create first test company."""
    return Company.objects.create(name="Test Company 1", slug="test-company-1")


@pytest.fixture
def company2(db):
    """Create second test company."""
    return Company.objects.create(name="Test Company 2", slug="test-company-2")


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
    CustomerProfile.objects.create(user=user, company=company1, phone_number="+998901111111")
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
    CustomerProfile.objects.create(user=user, company=company2, phone_number="+998902222222")
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return CustomUser.objects.create_user(
        username="admin",
        password="admin123",
        user_type="admin",
        is_staff=True,
    )


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def authenticated_customer_client(api_client, customer_user):
    """Create API client authenticated as customer."""
    api_client.force_authenticate(user=customer_user)
    return api_client


@pytest.mark.django_db
class TestCustomerAuthentication:
    """Tests for customer authentication."""

    def test_customer_can_login_with_username_password(self, api_client, customer_user):
        """Test customer login with username and password."""
        response = api_client.post(
            "/api/auth/login/",
            {"login": "customer1", "password": "password123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["user_type"] == "customer"
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["username"] == "customer1"
        assert response.data["user"]["company"]["name"] == "Test Company 1"

    def test_customer_cannot_login_with_wrong_password(self, api_client, customer_user):
        """Test customer login fails with wrong password."""
        response = api_client.post(
            "/api/auth/login/",
            {"login": "customer1", "password": "wrongpassword"},
            format="json",
        )

        # Custom exception handler returns 403 for authentication failures
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_customer_cannot_access_without_auth(self, api_client):
        """Test that unauthenticated users cannot access customer endpoints."""
        response = api_client.get("/api/customer/profile/")

        # Custom exception handler returns 403 for authentication failures
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestCustomerProfileAPI:
    """Tests for customer profile API endpoints."""

    def test_get_customer_profile(self, authenticated_customer_client, customer_user):
        """Test getting customer profile."""
        response = authenticated_customer_client.get("/api/customer/profile/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["id"] == customer_user.id
        assert response.data["data"]["username"] == "customer1"
        assert response.data["data"]["full_name"] == "Test Customer"
        assert response.data["data"]["company"]["name"] == "Test Company 1"

    def test_update_customer_profile(self, authenticated_customer_client, customer_user):
        """Test updating customer profile."""
        response = authenticated_customer_client.patch(
            "/api/customer/profile/update_profile/",
            {"first_name": "Updated", "last_name": "Name"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["first_name"] == "Updated"
        assert response.data["data"]["last_name"] == "Name"

        # Verify in database
        customer_user.refresh_from_db()
        assert customer_user.first_name == "Updated"
        assert customer_user.last_name == "Name"

    def test_update_customer_password(self, authenticated_customer_client, customer_user):
        """Test updating customer password."""
        response = authenticated_customer_client.patch(
            "/api/customer/profile/update_profile/",
            {"password": "newpassword123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify password was changed
        customer_user.refresh_from_db()
        assert customer_user.check_password("newpassword123") is True


@pytest.mark.django_db
class TestCustomerContainerAPI:
    """Tests for customer container API endpoints."""

    def test_list_company_containers(self, authenticated_customer_client, customer_user, company1):
        """Test listing containers filtered by customer's company."""
        # Create containers for customer's company
        container1 = Container.objects.create(container_number="HDMU6565958", iso_type="22G1")
        ContainerEntry.objects.create(
            container=container1,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="01A123BC",
            company=company1,
            recorded_by=customer_user,
        )

        response = authenticated_customer_client.get("/api/customer/containers/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["container"]["container_number"] == "HDMU6565958"

    def test_cannot_see_other_company_containers(
        self, authenticated_customer_client, customer_user, company1, company2
    ):
        """Test that customer cannot see other company's containers."""
        # Create container for different company
        container = Container.objects.create(container_number="HDMU6565959", iso_type="22G1")
        ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="01B456CD",
            company=company2,
            recorded_by=customer_user,
        )

        response = authenticated_customer_client.get("/api/customer/containers/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0  # Should not see company2's containers

    def test_filter_containers_by_status(self, authenticated_customer_client, customer_user, company1):
        """Test filtering containers by status."""
        # Create laden and empty containers
        container1 = Container.objects.create(container_number="HDMU6565960", iso_type="22G1")
        ContainerEntry.objects.create(
            container=container1,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="01A111AA",
            company=company1,
            recorded_by=customer_user,
        )

        container2 = Container.objects.create(container_number="HDMU6565961", iso_type="22G1")
        ContainerEntry.objects.create(
            container=container2,
            status="EMPTY",
            transport_type="TRUCK",
            transport_number="01A222BB",
            company=company1,
            recorded_by=customer_user,
        )

        # Filter for LADEN only
        response = authenticated_customer_client.get("/api/customer/containers/?status=LADEN")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["status"] == "LADEN"

    def test_get_container_detail(self, authenticated_customer_client, customer_user, company1):
        """Test getting specific container details."""
        container = Container.objects.create(container_number="HDMU6565962", iso_type="22G1")
        entry = ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRUCK",
            transport_number="01A333CC",
            company=company1,
            recorded_by=customer_user,
            client_name="Test Client",
            cargo_name="Test Cargo",
        )

        response = authenticated_customer_client.get(f"/api/customer/containers/{entry.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["container"]["container_number"] == "HDMU6565962"
        assert response.data["client_name"] == "Test Client"
        assert response.data["cargo_name"] == "Test Cargo"


@pytest.mark.django_db
class TestCustomerPreOrderAPI:
    """Tests for customer pre-order API endpoints."""

    def test_create_preorder(self, authenticated_customer_client, customer_user):
        """Test creating a new pre-order."""
        response = authenticated_customer_client.post(
            "/api/customer/preorders/",
            {
                "plate_number": "01A123BC",
                "operation_type": "LOAD",
                "notes": "Test order",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["plate_number"] == "01A123BC"
        assert response.data["data"]["operation_type"] == "LOAD"
        assert response.data["data"]["status"] == "PENDING"
        assert response.data["data"]["notes"] == "Test order"

        # Verify in database
        assert PreOrder.objects.filter(customer=customer_user).count() == 1

    def test_list_customer_preorders(self, authenticated_customer_client, customer_user):
        """Test listing customer's pre-orders."""
        # Create pre-orders
        PreOrder.objects.create(customer=customer_user, plate_number="01A111AA", operation_type="LOAD")
        PreOrder.objects.create(customer=customer_user, plate_number="01B222BB", operation_type="UNLOAD")

        response = authenticated_customer_client.get("/api/customer/preorders/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_cannot_see_other_customer_preorders(self, authenticated_customer_client, customer_user, customer_user2):
        """Test that customer cannot see other customer's pre-orders."""
        # Create pre-order for different customer
        PreOrder.objects.create(customer=customer_user2, plate_number="01C333CC", operation_type="LOAD")

        response = authenticated_customer_client.get("/api/customer/preorders/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0  # Should not see other customer's orders

    def test_get_preorder_detail(self, authenticated_customer_client, customer_user):
        """Test getting specific pre-order details."""
        preorder = PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A444DD",
            operation_type="LOAD",
            notes="Test notes",
        )

        response = authenticated_customer_client.get(f"/api/customer/preorders/{preorder.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["plate_number"] == "01A444DD"
        assert response.data["data"]["notes"] == "Test notes"

    def test_update_preorder_notes(self, authenticated_customer_client, customer_user):
        """Test updating pre-order notes."""
        preorder = PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A555EE",
            operation_type="LOAD",
            notes="Original notes",
        )

        response = authenticated_customer_client.patch(
            f"/api/customer/preorders/{preorder.id}/",
            {"notes": "Updated notes"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["notes"] == "Updated notes"

        # Verify in database
        preorder.refresh_from_db()
        assert preorder.notes == "Updated notes"

    def test_cancel_pending_preorder(self, authenticated_customer_client, customer_user):
        """Test cancelling a pending pre-order."""
        preorder = PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A666FF",
            operation_type="LOAD",
            status="PENDING",
        )

        response = authenticated_customer_client.delete(f"/api/customer/preorders/{preorder.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        # Verify order was cancelled
        preorder.refresh_from_db()
        assert preorder.status == "CANCELLED"
        assert preorder.cancelled_at is not None

    def test_cannot_cancel_matched_preorder(self, authenticated_customer_client, customer_user):
        """Test that matched pre-orders cannot be cancelled."""
        preorder = PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A777GG",
            operation_type="LOAD",
            status="MATCHED",
        )

        response = authenticated_customer_client.delete(f"/api/customer/preorders/{preorder.id}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_get_pending_preorders(self, authenticated_customer_client, customer_user):
        """Test getting only pending pre-orders."""
        # Create orders with different statuses
        PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A888HH",
            operation_type="LOAD",
            status="PENDING",
        )
        PreOrder.objects.create(
            customer=customer_user,
            plate_number="01A999II",
            operation_type="LOAD",
            status="MATCHED",
        )

        response = authenticated_customer_client.get("/api/customer/preorders/pending/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]  # Should have results
        # All returned orders should be PENDING
        for order in response.data["data"]:
            assert order["status"] == "PENDING"


@pytest.mark.django_db
class TestCustomerSecurityIsolation:
    """Tests for security and data isolation."""

    def test_customer_cannot_access_admin_endpoints(self, authenticated_customer_client):
        """Test that customers cannot access admin endpoints."""
        response = authenticated_customer_client.get("/api/auth/customers/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_customer_cannot_access_other_customer_preorder(self, api_client, customer_user, customer_user2):
        """Test that customer cannot access another customer's pre-order."""
        api_client.force_authenticate(user=customer_user)

        # Create pre-order for customer2
        preorder = PreOrder.objects.create(customer=customer_user2, plate_number="01AXXX", operation_type="LOAD")

        response = api_client.get(f"/api/customer/preorders/{preorder.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_cannot_access_customer_endpoints(self, api_client, admin_user):
        """Test that admin users cannot access customer-only endpoints."""
        api_client.force_authenticate(user=admin_user)

        response = api_client.get("/api/customer/profile/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
