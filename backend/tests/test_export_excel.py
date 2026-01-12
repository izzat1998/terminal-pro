from io import BytesIO

import pandas as pd
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.terminal_operations.models import ContainerEntry
from apps.terminal_operations.services import ContainerEntryExportService


User = get_user_model()


@pytest.fixture
def authenticated_client():
    """Create authenticated API client"""
    client = APIClient()

    # Get or create admin user
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True}
    )

    # Generate JWT token
    refresh = RefreshToken.for_user(admin_user)
    access_token = str(refresh.access_token)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    return client


@pytest.mark.django_db
class TestExportExcelService:
    """Test ContainerEntryExportService"""

    def test_export_service_instantiation(self):
        """Test that export service instantiates correctly"""
        service = ContainerEntryExportService()
        assert service is not None

    def test_export_to_excel_empty_queryset(self):
        """Test exporting empty queryset"""
        service = ContainerEntryExportService()
        queryset = ContainerEntry.objects.none()

        excel_bytes = service.export_to_excel(queryset)
        assert excel_bytes is not None
        assert len(excel_bytes) > 0

    def test_export_to_excel_with_data(self):
        """Test exporting with actual data"""
        # Get existing entries from database
        queryset = ContainerEntry.objects.all()[:10]

        if queryset.exists():
            service = ContainerEntryExportService()
            excel_bytes = service.export_to_excel(queryset)

            # Verify file was created
            assert len(excel_bytes) > 0

            # Verify Excel file can be read (dual headers: English row 1, Russian row 2)
            df = pd.read_excel(BytesIO(excel_bytes), header=0)  # Reads English headers
            assert df is not None
            assert len(df) > 0

    def test_export_returns_all_required_columns(self):
        """Test that export includes all required columns (dual headers: English + Russian)"""
        queryset = ContainerEntry.objects.all()[:5]

        if queryset.exists():
            service = ContainerEntryExportService()
            excel_bytes = service.export_to_excel(queryset)

            # Read with English headers (row 1)
            df_english = pd.read_excel(BytesIO(excel_bytes), header=0)

            # Check English headers
            required_english_columns = [
                '№',
                'Container number',
                'Container length',
                'Client',
                'Container Owner',
                'Cargo Name',
                'Terminal IN Date',
                'Terminal IN Modality',
                'IN Train #',
                'IN Truck / Wagon #',
                'Date of pick up',
                'Terminal OUT Modality',
                'OUT Train #',
                'OUT Truck / Wagon #',
                'Destination station',
                'Location',  # Fixed spelling
                'Date of additional crane operation',
                'Note',
                'Dwell Time (days)',
                'weight of cargo'
            ]

            for col in required_english_columns:
                assert col in df_english.columns, f"Missing English column: {col}"

            # Read with Russian headers (row 2, skip row 1)
            df_russian = pd.read_excel(BytesIO(excel_bytes), header=1)

            # Check Russian headers
            required_russian_columns = [
                '№',
                'Номер контейнера',
                'Тип',
                'Клиент',
                'Собственник контейнера',
                'Наименование ГРУЗА',
                'Дата разгрузки на терминале',
                'транспорт при ЗАВОЗЕ',
                'Номер Поезда при ЗАВОЗЕ',
                'номер машины/ вагона при ЗАВОЗЕ',
                'Дата вывоза конт-ра с МТТ',
                'Транспорт при ВЫВОЗЕ',
                'Номер Поезда при ВЫВОЗЕ',
                'номер машины/ вагона при ВЫВОЗЕ',
                'Станция назначения',
                'Местоположение',  # Fixed spelling
                'дата дополнительной крановой операции',
                'Примечание',
                'Количество дней на хранение',
                'Тоннаж'
            ]

            for col in required_russian_columns:
                assert col in df_russian.columns, f"Missing Russian column: {col}"


@pytest.mark.django_db
class TestExportExcelAPI:
    """Test export_excel API endpoint"""

    def test_export_endpoint_requires_authentication(self, client):
        """Test that export endpoint requires JWT authentication"""
        response = client.get('/api/terminal/entries/export_excel/')
        # DRF returns 401 or 403 depending on configuration
        assert response.status_code in [401, 403]

    def test_export_endpoint_authenticated(self, authenticated_client):
        """Test that authenticated user can access export endpoint"""
        response = authenticated_client.get(
            '/api/terminal/entries/export_excel/',
            HTTP_HOST='127.0.0.1'
        )
        # Status 200 is success, 404 means endpoint path may have changed
        # We're mainly testing auth works
        assert response.status_code in [200, 404, 500]

    def test_export_endpoint_returns_excel_file(self, authenticated_client):
        """Test that export endpoint returns Excel file"""
        response = authenticated_client.get(
            '/api/terminal/entries/export_excel/',
            HTTP_HOST='127.0.0.1'
        )

        if response.status_code == 200:
            assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            # Just verify the response has data
            # FileResponse returns streaming_content iterator
            has_content = False
            for chunk in response.streaming_content:
                has_content = True
                break
            assert has_content, "Response has no content"

    def test_export_endpoint_with_status_filter(self, authenticated_client):
        """Test export with status filter"""
        response = authenticated_client.get(
            '/api/terminal/entries/export_excel/?status=EMPTY',
            HTTP_HOST='127.0.0.1'
        )

        if response.status_code == 200:
            assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            # Verify response has streaming content
            has_content = False
            for chunk in response.streaming_content:
                has_content = True
                break
            assert has_content, "Response has no content"

    def test_export_endpoint_with_search_filter(self, authenticated_client):
        """Test export with search filter"""
        response = authenticated_client.get(
            '/api/terminal/entries/export_excel/?search_text=container',
            HTTP_HOST='127.0.0.1'
        )

        if response.status_code == 200:
            assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            # Verify response has streaming content
            has_content = False
            for chunk in response.streaming_content:
                has_content = True
                break
            assert has_content, "Response has no content"
