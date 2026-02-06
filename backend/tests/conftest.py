"""
Pytest configuration and fixtures for terminal_app tests.
"""
import os

import django
from django.conf import settings


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "terminal_app.settings")

# Use SQLite for tests to avoid PostgreSQL CREATE DATABASE permission issues
os.environ["DATABASE_URL"] = ""

if not settings.configured:
    django.setup()

# Force SQLite after Django setup
settings.DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(admin_user):
    """Authenticated API client with admin user."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def authenticated_client_with_token(admin_user):
    """Authenticated API client with JWT token."""
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    access_token = str(refresh.access_token)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    return client, admin_user


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        username='testadmin',
        email='admin@example.com',
        password='testpass123',
        is_admin=True,
        is_staff=True,
    )


@pytest.fixture
def regular_user(db):
    """Create a regular non-admin user."""
    return User.objects.create_user(
        username='testuser',
        email='user@example.com',
        password='testpass123',
    )


@pytest.fixture
def manager_user(db):
    """Create a manager user."""
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create(
        username='mgr_+998901234567',
        first_name='Test Manager',
        phone_number='+998901234567',
        user_type='manager',
        bot_access=True,
    )


@pytest.fixture
def customer_user(db):
    """Create a customer user."""
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create(
        username='customer_+998909876543',
        first_name='Test Customer',
        phone_number='+998909876543',
        user_type='customer',
        bot_access=True,
    )


# ============================================================================
# Container Fixtures
# ============================================================================

@pytest.fixture
def container(db):
    """Create a test container."""
    from apps.containers.models import Container
    return Container.objects.create(
        container_number='MSKU1234567',
        iso_type='42G1',
    )


@pytest.fixture
def container_factory(db):
    """Factory for creating containers with custom data."""
    from apps.containers.models import Container

    def _create_container(number=None, iso_type='42G1'):
        import random
        import string
        if number is None:
            prefix = ''.join(random.choices(string.ascii_uppercase, k=4))
            suffix = ''.join(random.choices(string.digits, k=7))
            number = f'{prefix}{suffix}'
        return Container.objects.create(
            container_number=number,
            iso_type=iso_type,
        )
    return _create_container


# ============================================================================
# Container Entry Fixtures
# ============================================================================

@pytest.fixture
def container_entry(container, admin_user):
    """Create a test container entry."""
    from apps.terminal_operations.models import ContainerEntry
    return ContainerEntry.objects.create(
        container=container,
        status='LADEN',
        transport_type='TRUCK',
        transport_number='ABC123',
        recorded_by=admin_user,
    )


@pytest.fixture
def container_entry_factory(container_factory, admin_user):
    """Factory for creating container entries."""
    from django.utils import timezone

    from apps.terminal_operations.models import ContainerEntry

    def _create_entry(
        container=None,
        status='LADEN',
        transport_type='TRUCK',
        transport_number=None,
        recorded_by=None,
        entry_time=None,
    ):
        if container is None:
            container = container_factory()
        if recorded_by is None:
            recorded_by = admin_user
        if entry_time is None:
            entry_time = timezone.now()

        return ContainerEntry.objects.create(
            container=container,
            status=status,
            transport_type=transport_type,
            transport_number=transport_number or 'TEST001',
            recorded_by=recorded_by,
            entry_time=entry_time,
        )
    return _create_entry


# ============================================================================
# Container Owner Fixtures
# ============================================================================

@pytest.fixture
def container_owner(db):
    """Create a test container owner."""
    from apps.terminal_operations.models import ContainerOwner
    return ContainerOwner.objects.create(name='Test Shipping Co')


@pytest.fixture
def container_owners(db):
    """Create multiple container owners."""
    from apps.terminal_operations.models import ContainerOwner
    return [
        ContainerOwner.objects.create(name='Owner A'),
        ContainerOwner.objects.create(name='Owner B'),
        ContainerOwner.objects.create(name='Owner C'),
    ]


# ============================================================================
# Vehicle Fixtures
# ============================================================================

@pytest.fixture
def destination(db):
    """Create a test destination."""
    from apps.vehicles.models import Destination
    return Destination.objects.create(
        name='Main Warehouse',
        zone='K1',
    )


@pytest.fixture
def vehicle_entry(admin_user, destination):
    """Create a test vehicle entry."""
    from django.utils import timezone

    from apps.vehicles.models import VehicleEntry

    return VehicleEntry.objects.create(
        license_plate='01A123BC',
        vehicle_type='CARGO',
        transport_type='TRUCK',
        entry_load_status='LOADED',
        cargo_type='CONTAINER',
        destination=destination,
        entry_time=timezone.now(),
        recorded_by=admin_user,
        status='ON_TERMINAL',
    )


# ============================================================================
# PreOrder Fixtures
# ============================================================================

@pytest.fixture
def preorder(customer_user):
    """Create a test pre-order."""
    from apps.terminal_operations.models import PreOrder
    return PreOrder.objects.create(
        customer=customer_user,
        plate_number='01A456BC',
        operation_type='LOAD',
        status='PENDING',
    )


# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def test_image():
    """Create a test image file."""
    import tempfile

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    image = Image.new('RGB', (100, 100), color='red')
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(temp_file, 'JPEG')
    temp_file.seek(0)

    return SimpleUploadedFile(
        name='test_image.jpg',
        content=temp_file.read(),
        content_type='image/jpeg',
    )


@pytest.fixture
def test_excel_file():
    """Create a test Excel file."""
    from io import BytesIO

    import pandas as pd
    from django.core.files.uploadedfile import SimpleUploadedFile

    df = pd.DataFrame({
        'Column1': ['A', 'B', 'C'],
        'Column2': [1, 2, 3],
    })

    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    return SimpleUploadedFile(
        name='test_file.xlsx',
        content=buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


# ============================================================================
# Django Settings Override
# ============================================================================

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Allow database access for all tests."""
    pass
