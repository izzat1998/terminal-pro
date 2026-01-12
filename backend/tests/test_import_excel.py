"""
Tests for ContainerEntryImportService - Excel import functionality.
Focuses on critical business logic: validation, duplicate handling, and data mapping.
"""
from datetime import datetime
from io import BytesIO

import pandas as pd
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.containers.models import Container
from apps.terminal_operations.models import ContainerEntry, ContainerOwner
from apps.terminal_operations.services.container_entry_import_service import (
    ContainerEntryImportService,
)


User = get_user_model()


@pytest.fixture
def import_service():
    """Fresh import service for each test."""
    return ContainerEntryImportService()


@pytest.fixture
def user():
    """Create an admin user for recording entries."""
    return User.objects.create_user(
        username="import_user",
        email="import@test.com",
        password="testpass123",
        is_admin=True,
    )


def create_excel_file(rows: list[dict]) -> bytes:
    """Helper to create Excel file bytes from row data."""
    df = pd.DataFrame(rows)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()


# Russian column names from the import service
REQUIRED_COLUMNS = {
    "container_number": "Номер контейнера",
    "iso_type": "Тип",
    "entry_date": "Дата разгрузки на терминале",
    "transport_type": "транспорт\nпри ЗАВОЗЕ",
}

OPTIONAL_COLUMNS = {
    "transport_number": "номер машины/ вагона \nпри ЗАВОЗЕ",
    "train_number": "Номер Поезда\nпри ЗАВОЗЕ",
    "client": "Клиент",
    "owner": "Собственник контейнера",
    "cargo": "Наименование ГРУЗА",
    "weight": "Тоннаж",
    "location": "Местоположение",
    "exit_date": "Дата вывоза конт-ра с МТТ",
    "exit_transport": "Транспорт\nпри ВЫВОЗЕ",
    "destination": "Станция назначения",
    "dwell_time": "Количество дней на хранение",
}


def make_valid_row(
    container_number="MSKU1234567",
    iso_type="42G1",
    entry_date="2025-01-15",
    transport_type="TRUCK",
    **extras,
):
    """Create a valid row with required fields and optional extras."""
    row = {
        REQUIRED_COLUMNS["container_number"]: container_number,
        REQUIRED_COLUMNS["iso_type"]: iso_type,
        REQUIRED_COLUMNS["entry_date"]: entry_date,
        REQUIRED_COLUMNS["transport_type"]: transport_type,
    }
    # Add optional columns
    for key, col_name in OPTIONAL_COLUMNS.items():
        row[col_name] = extras.get(key, "")
    return row


@pytest.mark.django_db
class TestValidImport:
    """Tests for successful import scenarios."""

    def test_import_single_valid_row(self, import_service, user):
        """Import single container entry with all required fields."""
        excel_data = create_excel_file([make_valid_row()])

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        assert result["statistics"]["successful"] == 1
        assert result["statistics"]["failed"] == 0

        # Verify entry was created
        entry = ContainerEntry.objects.first()
        assert entry.container.container_number == "MSKU1234567"
        assert entry.container.iso_type == "42G1"
        assert entry.transport_type == "TRUCK"
        assert entry.recorded_by == user

    def test_import_multiple_rows(self, import_service, user):
        """Import multiple valid entries in one file."""
        rows = [
            make_valid_row(container_number="ABCD1234567"),
            make_valid_row(container_number="EFGH7654321", iso_type="22G1"),
            make_valid_row(container_number="IJKL0000001", transport_type="WAGON"),
        ]
        excel_data = create_excel_file(rows)

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        assert result["statistics"]["successful"] == 3
        assert ContainerEntry.objects.count() == 3

    def test_import_with_optional_fields(self, import_service, user):
        """Import with optional business fields populated."""
        rows = [
            make_valid_row(
                client="Test Client",
                cargo="Steel Plates",
                weight="15000",
                location="Zone A",
            )
        ]
        excel_data = create_excel_file(rows)

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        entry = ContainerEntry.objects.first()
        assert entry.client_name == "Test Client"
        assert entry.cargo_name == "Steel Plates"
        assert entry.cargo_weight == 15000.0
        assert entry.location == "Zone A"


@pytest.mark.django_db
class TestDuplicateHandling:
    """Tests for duplicate detection and update logic."""

    def test_update_existing_entry_on_reimport(self, import_service, user):
        """Reimporting same container+date updates instead of creating duplicate."""
        # First import
        excel_data = create_excel_file(
            [make_valid_row(container_number="DUPE1234567", client="Original Client")]
        )
        result1 = import_service.import_from_excel(excel_data, user)
        assert result1["success"] is True

        first_entry = ContainerEntry.objects.first()
        original_id = first_entry.id

        # Reimport with updated data (same container + date)
        import_service = ContainerEntryImportService()  # fresh service
        excel_data = create_excel_file(
            [make_valid_row(container_number="DUPE1234567", client="Updated Client")]
        )
        result2 = import_service.import_from_excel(excel_data, user)

        assert result2["success"] is True
        # Should still be 1 entry
        assert ContainerEntry.objects.count() == 1

        # Entry should be updated
        updated_entry = ContainerEntry.objects.first()
        assert updated_entry.id == original_id
        assert updated_entry.client_name == "Updated Client"

    def test_different_dates_create_separate_entries(self, import_service, user):
        """Same container on different dates creates separate entries."""
        rows = [
            make_valid_row(container_number="SAME1234567", entry_date="2025-01-10"),
            make_valid_row(container_number="SAME1234567", entry_date="2025-01-20"),
        ]
        excel_data = create_excel_file(rows)

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        assert ContainerEntry.objects.count() == 2


@pytest.mark.django_db
class TestValidationErrors:
    """Tests for validation error handling."""

    def test_missing_container_number(self, import_service, user):
        """Missing container number causes row failure."""
        row = make_valid_row()
        row[REQUIRED_COLUMNS["container_number"]] = ""
        excel_data = create_excel_file([row])

        result = import_service.import_from_excel(excel_data, user)

        assert result["statistics"]["failed"] == 1
        assert ContainerEntry.objects.count() == 0
        assert "container number" in str(result["errors"]).lower()

    def test_missing_entry_date(self, import_service, user):
        """Missing entry date causes row failure."""
        row = make_valid_row()
        row[REQUIRED_COLUMNS["entry_date"]] = ""
        excel_data = create_excel_file([row])

        result = import_service.import_from_excel(excel_data, user)

        assert result["statistics"]["failed"] == 1
        assert "date" in str(result["errors"]).lower()

    def test_invalid_transport_type(self, import_service, user):
        """Invalid transport type causes row failure."""
        row = make_valid_row()
        row[REQUIRED_COLUMNS["transport_type"]] = "HELICOPTER"
        excel_data = create_excel_file([row])

        result = import_service.import_from_excel(excel_data, user)

        assert result["statistics"]["failed"] == 1
        assert "transport" in str(result["errors"]).lower()

    def test_invalid_iso_type(self, import_service, user):
        """Invalid ISO type causes row failure."""
        row = make_valid_row()
        row[REQUIRED_COLUMNS["iso_type"]] = "INVALID"
        excel_data = create_excel_file([row])

        result = import_service.import_from_excel(excel_data, user)

        assert result["statistics"]["failed"] == 1
        assert "iso type" in str(result["errors"]).lower()

    def test_partial_import_continues_after_error(self, import_service, user):
        """Valid rows import even when some rows fail."""
        rows = [
            make_valid_row(container_number="GOOD1234567"),  # valid
            make_valid_row(container_number=""),  # invalid - missing number
            make_valid_row(container_number="GOOD7654321"),  # valid
        ]
        excel_data = create_excel_file(rows)

        result = import_service.import_from_excel(excel_data, user)

        assert result["statistics"]["successful"] == 2
        assert result["statistics"]["failed"] == 1
        assert ContainerEntry.objects.count() == 2


@pytest.mark.django_db
class TestContainerOwnerCreation:
    """Tests for container owner on-the-fly creation."""

    def test_creates_new_container_owner(self, import_service, user):
        """Import creates ContainerOwner if not exists."""
        rows = [make_valid_row(owner="New Shipping Company")]
        excel_data = create_excel_file(rows)

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        owner = ContainerOwner.objects.filter(name="New Shipping Company").first()
        assert owner is not None
        assert ContainerEntry.objects.first().container_owner == owner

    def test_reuses_existing_container_owner(self, import_service, user):
        """Import reuses existing ContainerOwner by name."""
        existing_owner = ContainerOwner.objects.create(name="Existing Shipping Co")

        rows = [make_valid_row(owner="Existing Shipping Co")]
        excel_data = create_excel_file(rows)

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        # Should not create duplicate
        assert ContainerOwner.objects.filter(name="Existing Shipping Co").count() == 1
        assert ContainerEntry.objects.first().container_owner == existing_owner


@pytest.mark.django_db
class TestTransportTypeMapping:
    """Tests for transport type value mapping."""

    def test_map_truck(self, import_service, user):
        """TRUCK transport type is mapped correctly."""
        excel_data = create_excel_file([make_valid_row(transport_type="TRUCK")])
        import_service.import_from_excel(excel_data, user)

        assert ContainerEntry.objects.first().transport_type == "TRUCK"

    def test_map_wagon(self, import_service, user):
        """WAGON transport type is mapped correctly."""
        excel_data = create_excel_file([make_valid_row(transport_type="WAGON")])
        import_service.import_from_excel(excel_data, user)

        assert ContainerEntry.objects.first().transport_type == "WAGON"

    def test_map_train(self, import_service, user):
        """TRAIN transport type is mapped correctly."""
        excel_data = create_excel_file([make_valid_row(transport_type="TRAIN")])
        import_service.import_from_excel(excel_data, user)

        assert ContainerEntry.objects.first().transport_type == "TRAIN"


@pytest.mark.django_db
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_file(self, import_service, user):
        """Empty file (headers only) returns appropriate error."""
        df = pd.DataFrame(columns=list(REQUIRED_COLUMNS.values()))
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        excel_data = buffer.getvalue()

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is False
        assert "no data" in result["message"].lower()

    def test_nan_values_handled(self, import_service, user):
        """NaN values in optional fields don't cause errors."""
        row = make_valid_row()
        row[OPTIONAL_COLUMNS["client"]] = float("nan")
        row[OPTIONAL_COLUMNS["weight"]] = float("nan")
        excel_data = create_excel_file([row])

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        entry = ContainerEntry.objects.first()
        assert entry.client_name == ""
        assert entry.cargo_weight is None

    def test_container_created_if_not_exists(self, import_service, user):
        """Container is created on-the-fly if not in database."""
        excel_data = create_excel_file(
            [make_valid_row(container_number="NEWC1234567", iso_type="22G1")]
        )

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        container = Container.objects.get(container_number="NEWC1234567")
        assert container.iso_type == "22G1"

    def test_container_iso_type_updated(self, import_service, user):
        """Existing container ISO type is updated if different in import."""
        Container.objects.create(container_number="UPDT1234567", iso_type="22G1")

        excel_data = create_excel_file(
            [make_valid_row(container_number="UPDT1234567", iso_type="45G1")]
        )

        import_service.import_from_excel(excel_data, user)

        container = Container.objects.get(container_number="UPDT1234567")
        assert container.iso_type == "45G1"

    def test_date_parsing_various_formats(self, import_service, user):
        """Different date formats are parsed correctly."""
        # The service uses pandas Timestamp which handles many formats
        rows = [
            make_valid_row(
                container_number="DATE1234567", entry_date="2025-03-15 10:30:00"
            ),
        ]
        excel_data = create_excel_file(rows)

        result = import_service.import_from_excel(excel_data, user)

        assert result["success"] is True
        entry = ContainerEntry.objects.first()
        assert entry.entry_time.year == 2025
        assert entry.entry_time.month == 3
        assert entry.entry_time.day == 15
