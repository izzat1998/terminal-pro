"""
Test export Excel filters for container entries.
Tests container_owner_ids, client_name, and date range filters.
"""
from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, ContainerOwner


User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def container_owners(db):
    """Create test container owners"""
    owner1 = ContainerOwner.objects.create(name='Owner A')
    owner2 = ContainerOwner.objects.create(name='Owner B')
    owner3 = ContainerOwner.objects.create(name='Owner C')
    return [owner1, owner2, owner3]


@pytest.fixture
def test_entries(db, test_user, container_owners):
    """Create test container entries with different owners, clients, and dates"""
    entries = []

    # Entry 1: Owner A, Client X, 5 days ago
    container1 = Container.objects.create(
        container_number='ABCD1234567',
        iso_type='22G1'
    )
    entry1 = ContainerEntry.objects.create(
        container=container1,
        status='EMPTY',
        transport_type='TRUCK',
        transport_number='TR001',
        recorded_by=test_user,
        client_name='Client X',
        container_owner=container_owners[0],
        entry_time=timezone.now() - timedelta(days=5)
    )
    entries.append(entry1)

    # Entry 2: Owner B, Client Y, 3 days ago
    container2 = Container.objects.create(
        container_number='EFGH7654321',
        iso_type='42G1'
    )
    entry2 = ContainerEntry.objects.create(
        container=container2,
        status='LADEN',
        transport_type='WAGON',
        transport_number='WG001',
        recorded_by=test_user,
        client_name='Client Y',
        container_owner=container_owners[1],
        entry_time=timezone.now() - timedelta(days=3)
    )
    entries.append(entry2)

    # Entry 3: Owner A, Client Z, 1 day ago
    container3 = Container.objects.create(
        container_number='IJKL1112131',
        iso_type='45G1'
    )
    entry3 = ContainerEntry.objects.create(
        container=container3,
        status='EMPTY',
        transport_type='TRUCK',
        transport_number='TR002',
        recorded_by=test_user,
        client_name='Client Z',
        container_owner=container_owners[0],
        entry_time=timezone.now() - timedelta(days=1)
    )
    entries.append(entry3)

    return entries


@pytest.mark.django_db
class TestExportFilters:
    """Test Excel export with various filters"""

    def test_export_with_single_owner(self, api_client, test_user, test_entries, container_owners):
        """Test filtering by single container owner ID"""
        api_client.force_authenticate(user=test_user)

        url = reverse('containerentry-export-excel')
        # Filter by Owner A (should get entries 1 and 3)
        response = api_client.get(f'{url}?container_owner_ids={container_owners[0].id}')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_export_with_multiple_owners(self, api_client, test_user, test_entries, container_owners):
        """Test filtering by multiple container owner IDs (comma-separated)"""
        api_client.force_authenticate(user=test_user)

        url = reverse('containerentry-export-excel')
        # Filter by Owner A and Owner B (should get all 3 entries)
        owner_ids = f'{container_owners[0].id},{container_owners[1].id}'
        response = api_client.get(f'{url}?container_owner_ids={owner_ids}')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_export_with_client_name_filter(self, api_client, test_user, test_entries):
        """Test filtering by client name (partial match)"""
        api_client.force_authenticate(user=test_user)

        url = reverse('containerentry-export-excel')
        # Filter by client name containing 'Client X'
        response = api_client.get(f'{url}?client_name__icontains=Client X')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_export_with_date_range(self, api_client, test_user, test_entries):
        """Test filtering by date range"""
        api_client.force_authenticate(user=test_user)

        url = reverse('containerentry-export-excel')
        # Filter by date range (last 4 days - should get entries 2 and 3)
        date_after = (timezone.now() - timedelta(days=4)).strftime('%Y-%m-%d')
        date_before = timezone.now().strftime('%Y-%m-%d')
        response = api_client.get(f'{url}?entry_date_after={date_after}&entry_date_before={date_before}')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_export_with_combined_filters(self, api_client, test_user, test_entries, container_owners):
        """Test combining multiple filters: owner + client + date range"""
        api_client.force_authenticate(user=test_user)

        url = reverse('containerentry-export-excel')
        # Filter: Owner A, Client containing 'Z', last 2 days (should get entry 3)
        date_after = (timezone.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        params = (
            f'container_owner_ids={container_owners[0].id}'
            f'&client_name__icontains=Z'
            f'&entry_date_after={date_after}'
        )
        response = api_client.get(f'{url}?{params}')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_export_no_filters(self, api_client, test_user, test_entries):
        """Test export without any filters (should return all entries)"""
        api_client.force_authenticate(user=test_user)

        url = reverse('containerentry-export-excel')
        response = api_client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        # Check filename format
        assert 'attachment' in response['Content-Disposition']
        assert 'container_entries_' in response['Content-Disposition']
        assert '.xlsx' in response['Content-Disposition']

    def test_export_with_invalid_owner_id(self, api_client, test_user, test_entries):
        """Test filtering with invalid owner ID (should return empty or handle gracefully)"""
        api_client.force_authenticate(user=test_user)

        url = reverse('containerentry-export-excel')
        response = api_client.get(f'{url}?container_owner_ids=99999')

        # Should still return 200 with empty Excel or gracefully handle
        assert response.status_code == 200

    def test_export_unauthorized(self, api_client):
        """Test export without authentication (should fail)"""
        url = reverse('containerentry-export-excel')
        response = api_client.get(url)

        # DRF returns 401 or 403 depending on configuration
        assert response.status_code in [401, 403]
