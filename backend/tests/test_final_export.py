"""
Test export_excel endpoint with real frontend parameters
"""
from io import BytesIO

import pandas as pd
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, ContainerOwner


User = get_user_model()


@pytest.fixture
def authenticated_client():
    """Create authenticated API client"""
    client = APIClient()

    # Get or create admin user
    admin_user, _ = User.objects.get_or_create(
        username='testadmin',
        defaults={'email': 'testadmin@example.com', 'is_staff': True, 'is_superuser': True}
    )

    # Generate JWT token
    refresh = RefreshToken.for_user(admin_user)
    access_token = str(refresh.access_token)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    return client, admin_user


@pytest.fixture
def test_data(authenticated_client):
    """Create test data that matches frontend filters"""
    client, user = authenticated_client

    # Create container owners
    owner1, _ = ContainerOwner.objects.get_or_create(name="Test Owner 1")
    owner2, _ = ContainerOwner.objects.get_or_create(name="Test Owner 2")
    owner3, _ = ContainerOwner.objects.get_or_create(name="Test Owner 3")

    # Create containers
    container1, _ = Container.objects.get_or_create(
        container_number="HDMU6565958",
        defaults={'iso_type': '42G1'}
    )
    container2, _ = Container.objects.get_or_create(
        container_number="TOLU1234567",
        defaults={'iso_type': '22G1'}
    )
    container3, _ = Container.objects.get_or_create(
        container_number="MAEU9876543",
        defaults={'iso_type': '42G1'}
    )

    # Create entries matching frontend filters
    entry1 = ContainerEntry.objects.create(
        container=container1,
        status='LADEN',
        transport_type='TRUCK',  # DB value for "Авто"
        entry_time=timezone.now(),
        recorded_by=user,
        container_owner=owner2,  # This should match container_owner_id=2
        client_name="Test Client 1",
        cargo_name="Test Cargo"
    )

    # Entry that matches ISO type and owner but NOT transport type
    entry2 = ContainerEntry.objects.create(
        container=container3,
        status='EMPTY',
        transport_type='WAGON',  # Different transport type
        entry_time=timezone.now(),
        recorded_by=user,
        container_owner=owner2,
        client_name="Test Client 2"
    )

    # Entry that matches transport type but NOT owner or ISO type
    entry3 = ContainerEntry.objects.create(
        container=container2,
        status='LADEN',
        transport_type='TRUCK',
        entry_time=timezone.now(),
        recorded_by=user,
        container_owner=owner1,  # Different owner
        client_name="Test Client 3"
    )

    return {
        'owners': [owner1, owner2, owner3],
        'containers': [container1, container2, container3],
        'entries': [entry1, entry2, entry3]
    }


@pytest.mark.django_db
class TestExportExcelWithFrontendFilters:
    """Test export_excel with real frontend parameters"""

    def test_export_with_single_container_owner_id(self, authenticated_client, test_data):
        """Test export with container_owner_id=2 (singular, like frontend sends)"""
        client, user = authenticated_client

        # Frontend sends container_owner_id (singular)
        response = client.get(
            '/api/terminal/entries/export_excel/?container_owner_id=2',
            HTTP_HOST='127.0.0.1'
        )

        print("\nTest: container_owner_id=2")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            # Read Excel file
            excel_bytes = b''.join(response.streaming_content)
            df = pd.read_excel(BytesIO(excel_bytes))
            print(f"Rows returned: {len(df)}")
            print(f"Owners in results: {df['Собственник контейнера'].unique()}")

            # This might FAIL because filter expects container_owner_ids (plural)
            # If it returns all entries, we have a bug

    def test_export_with_plural_container_owner_ids(self, authenticated_client, test_data):
        """Test export with container_owner_ids=2 (plural, what filter expects)"""
        client, user = authenticated_client

        # Try with plural version
        response = client.get(
            '/api/terminal/entries/export_excel/?container_owner_ids=2',
            HTTP_HOST='127.0.0.1'
        )

        print("\nTest: container_owner_ids=2 (plural)")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            excel_bytes = b''.join(response.streaming_content)
            df = pd.read_excel(BytesIO(excel_bytes))
            print(f"Rows returned: {len(df)}")
            print(f"Owners in results: {df['Собственник контейнера'].unique()}")

            # This should work correctly

    def test_export_with_frontend_exact_url(self, authenticated_client, test_data):
        """Test with exact frontend URL parameters"""
        client, user = authenticated_client

        # Exact frontend parameters:
        # container_iso_type=42G1
        # transport_type=Авто (Russian)
        # container_owner_id=2 (singular)
        response = client.get(
            '/api/terminal/entries/export_excel/?container_iso_type=42G1&transport_type=Авто&container_owner_id=2',
            HTTP_HOST='127.0.0.1'
        )

        print("\nTest: Frontend exact URL (container_iso_type=42G1&transport_type=Авто&container_owner_id=2)")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            excel_bytes = b''.join(response.streaming_content)
            df = pd.read_excel(BytesIO(excel_bytes))
            print(f"Rows returned: {len(df)}")
            print("\nDetails:")
            print(f"ISO types: {df['Тип контейнера'].unique()}")
            print(f"Transport types: {df['Транспорт при ЗАВОЗЕ'].unique()}")
            print(f"Owners: {df['Собственник контейнера'].unique()}")

            # Expected: 1 row (entry1) matching all filters
            # If container_owner_id doesn't work, we'll get 2 rows (entry1 + entry2)

    def test_export_with_corrected_url(self, authenticated_client, test_data):
        """Test with corrected URL (using container_owner_ids plural)"""
        client, user = authenticated_client

        # Corrected parameters:
        # container_iso_type=42G1
        # transport_type=Авто
        # container_owner_ids=2 (plural)
        response = client.get(
            '/api/terminal/entries/export_excel/?container_iso_type=42G1&transport_type=Авто&container_owner_ids=2',
            HTTP_HOST='127.0.0.1'
        )

        print("\nTest: Corrected URL (container_owner_ids=2, plural)")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            excel_bytes = b''.join(response.streaming_content)
            df = pd.read_excel(BytesIO(excel_bytes))
            print(f"Rows returned: {len(df)}")
            print("\nDetails:")
            print(f"ISO types: {df['Тип контейнера'].unique()}")
            print(f"Transport types: {df['Транспорт при ЗАВОЗЕ'].unique()}")
            print(f"Owners: {df['Собственник контейнера'].unique()}")

            # Expected: 1 row (entry1) matching all filters

    def test_check_filter_definitions(self):
        """Check what filters are actually defined"""
        from apps.terminal_operations.filters import ContainerEntryFilter

        print("\n=== Checking ContainerEntryFilter ===")
        filter_instance = ContainerEntryFilter()

        print("\nDeclared filters:")
        for filter_name in filter_instance.filters.keys():
            print(f"  - {filter_name}")

        print("\nMeta fields:")
        if hasattr(ContainerEntryFilter.Meta, 'fields'):
            fields = ContainerEntryFilter.Meta.fields
            # Handle both dict and list formats
            if isinstance(fields, dict):
                for field_name in fields.keys():
                    print(f"  - {field_name}")
            elif isinstance(fields, (list, tuple)):
                for field_name in fields:
                    print(f"  - {field_name}")

        # Check specifically for container_owner filters
        print("\nContainer owner related filters:")
        owner_filters = [f for f in filter_instance.filters.keys() if 'owner' in f.lower()]
        for f in owner_filters:
            print(f"  - {f}")
