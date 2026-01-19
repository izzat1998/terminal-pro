import pytest
from datetime import date, datetime
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Company, CustomUser, CustomerProfile
from apps.billing.models import Tariff, TariffRate
from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer_user(db):
    user = CustomUser.objects.create_user(
        username="customer", password="test123", user_type="customer"
    )
    return user


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", billing_method="split")


@pytest.fixture
def customer_with_profile(customer_user, company):
    CustomerProfile.objects.create(
        user=customer_user,
        company=company,
        phone_number="+998901234567",
    )
    return customer_user


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(
        username="admin", password="test123", user_type="admin"
    )


@pytest.fixture
def general_tariff(db, admin_user):
    tariff = Tariff.objects.create(
        effective_from=date(2025, 1, 1),
        created_by=admin_user,
    )
    TariffRate.objects.create(
        tariff=tariff,
        container_size="40ft",
        container_status="laden",
        daily_rate_usd=Decimal("15.00"),
        daily_rate_uzs=Decimal("195000.00"),
        free_days=3,
    )
    return tariff


@pytest.fixture
def container(db):
    return Container.objects.create(container_number="HDMU1234567", iso_type="42G1")


@pytest.fixture
def container_entry(db, container, company, admin_user):
    return ContainerEntry.objects.create(
        container=container,
        company=company,
        entry_time=timezone.make_aware(datetime(2026, 1, 5, 10, 0, 0)),
        status="LADEN",
        transport_type="TRUCK",
        transport_number="01A123BC",
        recorded_by=admin_user,
    )


@pytest.mark.django_db
class TestStatementAPI:
    def test_get_statement_unauthenticated(self, api_client):
        """Unauthenticated requests should be rejected."""
        url = "/api/customer/billing/statements/2026/1/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_statement_authenticated(
        self, api_client, customer_with_profile, company, container_entry, general_tariff
    ):
        """Authenticated customer should get/generate statement."""
        api_client.force_authenticate(user=customer_with_profile)
        url = "/api/customer/billing/statements/2026/1/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["year"] == 2026
        assert response.data["data"]["month"] == 1
        assert "line_items" in response.data["data"]

    def test_get_available_periods(
        self, api_client, customer_with_profile, company, container_entry, general_tariff
    ):
        """Customer should get available billing periods."""
        api_client.force_authenticate(user=customer_with_profile)
        url = "/api/customer/billing/available-periods/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(response.data["data"]) >= 1
