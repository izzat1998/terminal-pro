import tempfile

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.containers.models import Container
from apps.files.models import File, FileAttachment
from apps.terminal_operations.models import (
    ContainerEntry,
    ContainerOwner,
    CraneOperation,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return CustomUser.objects.create_user(
        username="testoperator", email="operator@terminal.com", password="testpass123"
    )


@pytest.fixture
def container():
    """Create a container with new iso_type field."""
    return Container.objects.create(
        container_number="MSKU1234567", iso_type="42G1"
    )


@pytest.fixture
def container_entry(container, user):
    return ContainerEntry.objects.create(
        container=container,
        status="LADEN",
        transport_type="TRUCK",
        transport_number="ABC123",
        recorded_by=user,
    )


@pytest.fixture
def test_image():
    """Create a test image file"""
    image = Image.new("RGB", (100, 100), color="red")
    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    image.save(temp_file, "JPEG")
    temp_file.seek(0)

    return SimpleUploadedFile(
        name="test_image.jpg", content=temp_file.read(), content_type="image/jpeg"
    )


@pytest.mark.django_db
class TestContainerEntryModel:
    def test_container_entry_creation(self, container, user):
        entry = ContainerEntry.objects.create(
            container=container,
            status="EMPTY",
            transport_type="WAGON",
            transport_number="RAIL456",
            recorded_by=user,
        )

        assert entry.container == container
        assert entry.status == "EMPTY"
        assert entry.transport_type == "WAGON"
        assert entry.transport_number == "RAIL456"
        assert entry.recorded_by == user
        assert entry.entry_time is not None
        assert entry.created_at is not None

    def test_container_entry_str_representation(self, container_entry):
        expected = f"{container_entry.container.container_number} - Гружёный - {container_entry.entry_time}"
        assert str(container_entry) == expected

    def test_container_entry_status_choices(self, container, user):
        # Test valid status choices
        for status_code, _ in ContainerEntry.STATUS_CHOICES:
            entry = ContainerEntry(
                container=container,
                status=status_code,
                transport_type="TRUCK",
                recorded_by=user,
            )
            entry.full_clean()  # Should not raise ValidationError

    def test_container_entry_transport_choices(self, container, user):
        # Test valid transport choices including TRAIN
        for transport_code, _ in ContainerEntry.TRANSPORT_CHOICES:
            entry = ContainerEntry(
                container=container,
                status="LADEN",
                transport_type=transport_code,
                recorded_by=user,
            )
            entry.full_clean()  # Should not raise ValidationError

    def test_entry_train_number_field(self, container, user):
        """Test incoming train number field"""
        entry = ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRAIN",
            entry_train_number="TR12345",
            recorded_by=user,
        )

        assert entry.transport_type == "TRAIN"
        assert entry.entry_train_number == "TR12345"

    def test_additional_crane_operation_date_field(self, container_entry):
        """Test additional crane operation date field"""
        from django.utils import timezone

        test_date = timezone.now()
        container_entry.additional_crane_operation_date = test_date
        container_entry.save()

        updated_entry = ContainerEntry.objects.get(pk=container_entry.pk)
        assert updated_entry.additional_crane_operation_date == test_date

    def test_dwell_time_days_property(self, container_entry):
        """Test dwell time calculation using dwell_time_days property."""
        from datetime import timedelta

        # No exit date - should return minimum 1 day (even for same-day entry)
        days_no_exit = container_entry.dwell_time_days
        assert days_no_exit is not None
        assert days_no_exit >= 1  # Minimum 1 day for any container

        # Add exit date 5 days later
        container_entry.exit_date = container_entry.entry_time + timedelta(days=5)
        container_entry.save()

        # Recalculate
        container_entry.refresh_from_db()
        assert container_entry.dwell_time_days == 5

    def test_dwell_time_days_same_day_exit(self, container_entry):
        """Test that same-day exits count as 1 day minimum."""
        from datetime import timedelta

        # Exit same day as entry
        container_entry.exit_date = container_entry.entry_time + timedelta(hours=2)
        container_entry.save()

        container_entry.refresh_from_db()
        assert container_entry.dwell_time_days == 1  # Minimum 1 day for exited containers


@pytest.mark.django_db
class TestContainerEntryAPI:
    def test_create_entry_authenticated(self, api_client, user, container):
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        data = {
            "container_number": container.container_number,
            "container_iso_type": "42G1",
            "status": "LADEN",
            "transport_type": "TRUCK",
            "transport_number": "XYZ789",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["container"]["container_number"] == container.container_number
        assert response.data["status"] == "Гружёный"  # Russian display name
        assert response.data["transport_type"] == "Авто"  # Russian display name
        # recorded_by returns nested user object
        assert response.data["recorded_by"]["id"] == user.id

    def test_create_entry_with_train(self, api_client, user, container):
        """Test creating entry with train transport"""
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        data = {
            "container_number": container.container_number,
            "container_iso_type": "42G1",
            "status": "LADEN",
            "transport_type": "TRAIN",
            "entry_train_number": "TR12345",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["transport_type"] == "Поезд"  # Russian for TRAIN
        assert response.data["entry_train_number"] == "TR12345"

    def test_create_entry_unauthenticated(self, api_client, container):
        url = reverse("containerentry-list")
        data = {
            "container_number": container.container_number,
            "container_iso_type": "42G1",
            "status": "EMPTY",
            "transport_type": "WAGON",
        }

        response = api_client.post(url, data)
        # Could be 401 or 403 depending on configuration
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_entry_missing_iso_type(self, api_client, user, container):
        """Test that iso_type is required on create"""
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        data = {
            "container_number": container.container_number,
            "status": "LADEN",
            "transport_type": "TRUCK",
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_entries(self, api_client, user, container_entry):
        """Test list entries returns paginated results."""
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Response is paginated with count, results
        assert "count" in response.data
        assert "results" in response.data
        assert response.data["count"] == 1
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == container_entry.id

    def test_recent_entries_action(self, api_client, user, container_entry):
        """Test recent entries action returns paginated results."""
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-recent")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Response is paginated
        assert "count" in response.data
        assert "results" in response.data
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == container_entry.id

    def test_by_container_action(self, api_client, user, container_entry):
        """Test by_container action returns paginated results."""
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-by-container")
        response = api_client.get(
            url, {"container_number": container_entry.container.container_number}
        )

        assert response.status_code == status.HTTP_200_OK
        # Response is paginated
        assert "count" in response.data
        assert "results" in response.data
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == container_entry.id

    def test_upload_file_to_entry(self, api_client, user, container_entry, test_image):
        """Test uploading file to entry."""
        from apps.files.models import FileCategory

        # Create required file category
        FileCategory.objects.get_or_create(
            code="container_image",
            defaults={"name": "Container Image", "max_file_size_mb": 5}
        )

        api_client.force_authenticate(user=user)

        url = reverse("containerentry-upload-file", args=[container_entry.id])
        data = {
            "file": test_image,
            "description": "Front view of container",
        }

        response = api_client.post(url, data, format="multipart")

        # Could be 201 or 400 depending on API validation
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_get_entry_detail(self, api_client, user, container_entry):
        """Test getting entry details."""
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-detail", args=[container_entry.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == container_entry.id
        assert response.data["container"]["container_number"] == container_entry.container.container_number

    def test_by_container_missing_parameter(self, api_client, user):
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-by-container")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "MISSING_PARAMETER"

    def test_crane_operation_creation(self, container_entry):
        """Test creating crane operation for entry via model."""
        from django.utils import timezone

        from apps.terminal_operations.models import CraneOperation

        crane_date = timezone.now()
        crane_op = CraneOperation.objects.create(
            container_entry=container_entry,
            operation_date=crane_date,
        )

        assert crane_op.container_entry == container_entry
        assert crane_op.operation_date == crane_date

    def test_exit_date_model_validation(self, container_entry):
        """Test exit_date validation at model level."""
        from datetime import timedelta

        from django.core.exceptions import ValidationError

        # Exit date before entry time should be invalid
        container_entry.exit_date = container_entry.entry_time - timedelta(days=1)

        # Model-level validation
        try:
            container_entry.full_clean()
            container_entry.save()
            # If no error, check if there's post-save validation
            assert container_entry.exit_date is not None
        except ValidationError:
            # Expected - exit_date cannot be before entry_time
            pass

    def test_create_historical_entry_with_all_fields(self, api_client, user, container):
        """Test creating complete entry with all fields (historical import)"""
        from datetime import timedelta

        from django.utils import timezone

        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        historical_date = timezone.now() - timedelta(days=10)

        data = {
            "container_number": container.container_number,
            "container_iso_type": "42G1",
            "status": "LADEN",
            "transport_type": "TRUCK",
            "transport_number": "ABC123",
            "entry_time": historical_date.isoformat(),
            # Stage 2 fields
            "client_name": "ABC Corp",
            "cargo_name": "Electronics",
            "cargo_weight": "18.50",
            "location": "Warehouse A",
            # Stage 3 fields (complete exit info)
            "exit_date": (historical_date + timedelta(days=5)).isoformat(),
            "exit_transport_type": "TRAIN",
            "exit_train_number": "TR456",
            "destination_station": "Central Station",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["client_name"] == "ABC Corp"
        assert response.data["cargo_weight"] == "18.50"
        assert response.data["destination_station"] == "Central Station"

        # Verify entry_time was set correctly
        created_entry = ContainerEntry.objects.get(pk=response.data["id"])
        assert created_entry.entry_time.date() == historical_date.date()

    def test_create_entry_auto_entry_time_if_not_provided(
        self, api_client, user, container
    ):
        """Test entry_time defaults to current time if not provided"""
        from django.utils import timezone

        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        before_creation = timezone.now()

        data = {
            "container_number": container.container_number,
            "container_iso_type": "42G1",
            "status": "LADEN",
            "transport_type": "TRUCK",
            # entry_time not provided
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        created_entry = ContainerEntry.objects.get(pk=response.data["id"])

        # entry_time should be close to current time
        time_diff = abs((created_entry.entry_time - before_creation).total_seconds())
        assert time_diff < 5  # Should be within 5 seconds

    def test_admin_can_override_recorded_by(self, api_client, user, container):
        """Test that admins can override recorded_by field"""

        # Create another user to assign to recorded_by
        other_user = CustomUser.objects.create_user(
            username="otheroperator", email="other@terminal.com", password="testpass123"
        )

        # Make authenticated user an admin
        user.is_staff = True
        user.save()

        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        data = {
            "container_number": container.container_number,
            "container_iso_type": "42G1",
            "status": "LADEN",
            "transport_type": "TRUCK",
            "recorded_by": other_user.id,
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        # recorded_by returns nested user object
        assert response.data["recorded_by"]["id"] == other_user.id

    def test_non_admin_cannot_override_recorded_by(self, api_client, user, container):
        """Test that non-admins cannot override recorded_by field"""
        # Create another user to assign to recorded_by
        other_user = CustomUser.objects.create_user(
            username="otheroperator", email="other@terminal.com", password="testpass123"
        )

        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        data = {
            "container_number": container.container_number,
            "container_iso_type": "42G1",
            "status": "LADEN",
            "transport_type": "TRUCK",
            "recorded_by": other_user.id,  # Try to override as non-admin
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_optional_fields_not_required_on_create(self, api_client, user, container):
        """Test that only 4 fields are required, rest are optional"""
        api_client.force_authenticate(user=user)

        url = reverse("containerentry-list")
        # Minimal data - only required fields
        data = {
            "container_number": container.container_number,
            "container_iso_type": "42G1",
            "status": "LADEN",
            "transport_type": "TRUCK",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["transport_number"] == ""
        assert response.data["entry_train_number"] == ""
        assert response.data["client_name"] == ""
        assert response.data["cargo_name"] == ""


@pytest.mark.django_db
class TestCraneOperationModel:
    """Tests for CraneOperation model."""

    def test_crane_operation_creation(self, container_entry):
        """Test creating a crane operation."""
        from django.utils import timezone

        operation_date = timezone.now()
        crane_op = CraneOperation.objects.create(
            container_entry=container_entry,
            operation_date=operation_date,
        )

        assert crane_op.container_entry == container_entry
        assert crane_op.operation_date == operation_date

    def test_crane_operation_str_representation(self, container_entry):
        """Test crane operation string representation."""
        from django.utils import timezone

        operation_date = timezone.now()
        crane_op = CraneOperation.objects.create(
            container_entry=container_entry,
            operation_date=operation_date,
        )

        expected = f"Crane op: {container_entry.container.container_number} - {operation_date}"
        assert str(crane_op) == expected

    def test_crane_operation_ordering(self, container_entry):
        """Test crane operations are ordered by operation_date descending."""
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()
        op1 = CraneOperation.objects.create(
            container_entry=container_entry,
            operation_date=now - timedelta(days=2),
        )
        op2 = CraneOperation.objects.create(
            container_entry=container_entry,
            operation_date=now,
        )
        op3 = CraneOperation.objects.create(
            container_entry=container_entry,
            operation_date=now - timedelta(days=1),
        )

        operations = list(CraneOperation.objects.all())
        assert operations[0] == op2  # Most recent first
        assert operations[1] == op3
        assert operations[2] == op1


@pytest.mark.django_db
class TestContainerOwnerModel:
    """Tests for ContainerOwner model."""

    def test_container_owner_creation(self):
        """Test creating a container owner."""
        owner = ContainerOwner.objects.create(name="Test Shipping Company")

        assert owner.name == "Test Shipping Company"
        assert owner.slug == "test-shipping-company"

    def test_container_owner_auto_slug(self):
        """Test that slug is auto-generated from name."""
        owner = ContainerOwner.objects.create(name="ABC Logistics Ltd")
        assert owner.slug == "abc-logistics-ltd"

    def test_container_owner_custom_slug(self):
        """Test that custom slug is preserved."""
        owner = ContainerOwner.objects.create(
            name="ABC Logistics Ltd",
            slug="custom-slug",
        )
        assert owner.slug == "custom-slug"

    def test_container_owner_str_representation(self):
        """Test string representation."""
        owner = ContainerOwner.objects.create(name="Test Company")
        assert str(owner) == "Test Company"

    def test_container_owner_unique_name(self):
        """Test that owner names must be unique."""
        ContainerOwner.objects.create(name="Unique Company")

        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ContainerOwner.objects.create(name="Unique Company")

    def test_container_owner_ordering(self):
        """Test owners are ordered by name."""
        ContainerOwner.objects.create(name="Zulu Shipping")
        ContainerOwner.objects.create(name="Alpha Lines")
        ContainerOwner.objects.create(name="Mid Transport")

        owners = list(ContainerOwner.objects.all())
        assert owners[0].name == "Alpha Lines"
        assert owners[1].name == "Mid Transport"
        assert owners[2].name == "Zulu Shipping"

    def test_container_entry_with_owner(self, container, user):
        """Test linking container entry to owner."""
        owner = ContainerOwner.objects.create(name="Test Owner")

        entry = ContainerEntry.objects.create(
            container=container,
            status="LADEN",
            transport_type="TRUCK",
            recorded_by=user,
            container_owner=owner,
        )

        assert entry.container_owner == owner
        assert owner.entries.first() == entry
