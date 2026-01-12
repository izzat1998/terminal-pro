#!/usr/bin/env python
"""
Test script to verify that filters work correctly with frontend query parameters.

Example frontend query:
https://api-mtt.xlog.uz/api/terminal/entries/?page=1&page_size=25&container_owner=1121&cargo_name=12112&entry_time=2025.11.10&entry_train_number=112&transport_number=121212
"""

import os

import django


# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'terminal_app.settings')
django.setup()

from django.test import RequestFactory

from apps.terminal_operations.filters import ContainerEntryFilter
from apps.terminal_operations.models import ContainerEntry


def test_filters():
    """Test various filter scenarios matching frontend usage"""

    print("=" * 80)
    print("Testing ContainerEntry Filters")
    print("=" * 80)

    # Create a mock request
    factory = RequestFactory()

    # Test 1: Date filter with dots (YYYY.MM.DD)
    print("\n1. Testing entry_time filter with YYYY.MM.DD format:")
    request = factory.get('/api/terminal/entries/', {'entry_time': '2025.11.10'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")
    print(f"   Errors: {filterset.errors if not filterset.is_valid() else 'None'}")

    # Test 2: Container owner text search
    print("\n2. Testing container_owner filter (text search):")
    request = factory.get('/api/terminal/entries/', {'container_owner': '1121'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")

    # Test 3: Cargo name partial search
    print("\n3. Testing cargo_name filter (partial match):")
    request = factory.get('/api/terminal/entries/', {'cargo_name': '12112'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")

    # Test 4: Entry train number partial search
    print("\n4. Testing entry_train_number filter (partial match):")
    request = factory.get('/api/terminal/entries/', {'entry_train_number': '112'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")

    # Test 5: Transport number partial search
    print("\n5. Testing transport_number filter (partial match):")
    request = factory.get('/api/terminal/entries/', {'transport_number': '121212'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")

    # Test 6: Combined filters (matching frontend example)
    print("\n6. Testing combined filters (frontend example):")
    request = factory.get('/api/terminal/entries/', {
        'page': '1',
        'page_size': '25',
        'container_owner': '1121',
        'cargo_name': '12112',
        'entry_time': '2025.11.10',
        'entry_train_number': '112',
        'transport_number': '121212'
    })
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")
    print(f"   Result count: {filterset.qs.count()}")

    # Test 7: Exit date with dots
    print("\n7. Testing exit_date filter with YYYY.MM.DD format:")
    request = factory.get('/api/terminal/entries/', {'exit_date': '2025.11.15'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")

    # Test 8: Status filter (Russian name)
    print("\n8. Testing status filter with Russian name:")
    request = factory.get('/api/terminal/entries/', {'status': 'Порожний'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")

    # Test 9: Transport type filter (Russian name)
    print("\n9. Testing transport_type filter with Russian name:")
    request = factory.get('/api/terminal/entries/', {'transport_type': 'Авто'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")

    # Test 10: Client name partial search
    print("\n10. Testing client_name filter (partial match):")
    request = factory.get('/api/terminal/entries/', {'client_name': 'TestClient'})
    filterset = ContainerEntryFilter(request.GET, queryset=ContainerEntry.objects.all())
    print(f"   Query params: {dict(request.GET)}")
    print(f"   SQL query filters: {filterset.qs.query}")
    print(f"   Is valid: {filterset.is_valid()}")

    print("\n" + "=" * 80)
    print("All filter tests completed!")
    print("=" * 80)


if __name__ == '__main__':
    test_filters()
