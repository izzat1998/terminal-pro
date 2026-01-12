import pytest
from django.core.exceptions import ValidationError

from apps.containers.models import Container


@pytest.mark.django_db
class TestContainerModel:
    """Tests for Container model with ISO 6346 type codes."""

    def test_container_creation_valid(self):
        """Test creating a container with valid data."""
        container = Container.objects.create(
            container_number="MSKU1234567", iso_type="42G1"
        )

        assert container.container_number == "MSKU1234567"
        assert container.iso_type == "42G1"
        assert container.created_at is not None
        assert container.updated_at is not None

    def test_container_number_validation_valid_formats(self):
        """Test valid container number formats (4 letters + 7 digits)."""
        valid_numbers = ["MSKU1234567", "ABCD9876543", "TEST0000001"]

        for i, number in enumerate(valid_numbers):
            container = Container(
                container_number=number, iso_type="22G1"
            )
            container.full_clean()  # Should not raise ValidationError

    def test_container_number_validation_invalid_formats(self):
        """Test invalid container number formats."""
        invalid_numbers = [
            "MSK1234567",    # Only 3 letters
            "MSKU12345678",  # 8 digits
            "MSKU123456",    # 6 digits
            "1234MSKU567",   # Numbers first
            "MSKU12X4567",   # Letter in number part
            "MSKU-1234567",  # Hyphen
        ]

        for number in invalid_numbers:
            container = Container(
                container_number=number, iso_type="22G1"
            )
            with pytest.raises(ValidationError):
                container.full_clean()

    def test_container_number_unique_constraint(self):
        """Test that container numbers must be unique."""
        Container.objects.create(
            container_number="MSKU1234567", iso_type="22G1"
        )

        with pytest.raises(ValidationError):
            Container.objects.create(
                container_number="MSKU1234567", iso_type="42G1"
            )

    def test_container_number_uppercase_conversion(self):
        """Test that container numbers are converted to uppercase."""
        container = Container(
            container_number="msku1234567",  # lowercase input
            iso_type="22G1",
        )
        container.save()

        assert container.container_number == "MSKU1234567"

    def test_container_iso_type_choices(self):
        """Test valid ISO type choices."""
        valid_types = ["22G1", "42G1", "45G1", "22R1", "42R1"]

        for i, iso_type in enumerate(valid_types):
            container = Container(
                container_number=f"TEST123456{i}",
                iso_type=iso_type,
            )
            container.full_clean()  # Should not raise ValidationError

    def test_container_str_representation(self):
        """Test container string representation."""
        container = Container.objects.create(
            container_number="MSKU1234567", iso_type="42G1"
        )

        expected_str = "MSKU1234567 (42G1)"
        assert str(container) == expected_str

    def test_container_ordering(self):
        """Test containers are ordered by container_number."""
        Container.objects.create(container_number="ZZZZ9999999", iso_type="22G1")
        Container.objects.create(container_number="AAAA0000001", iso_type="22G1")
        Container.objects.create(container_number="MSKU1234567", iso_type="22G1")

        containers = list(Container.objects.all())

        assert containers[0].container_number == "AAAA0000001"
        assert containers[1].container_number == "MSKU1234567"
        assert containers[2].container_number == "ZZZZ9999999"

    def test_container_meta_verbose_names(self):
        """Test model verbose names are in Russian."""
        assert Container._meta.verbose_name == "Контейнер"
        assert Container._meta.verbose_name_plural == "Контейнеры"

    def test_container_help_text(self):
        """Test container number field has help text."""
        field = Container._meta.get_field("container_number")
        assert "4 буквы + 7 цифр" in field.help_text

    def test_container_timestamps_inherited(self):
        """Test that Container inherits timestamp functionality from TimestampedModel."""
        container = Container.objects.create(
            container_number="MSKU1234567", iso_type="22G1"
        )

        assert hasattr(container, "created_at")
        assert hasattr(container, "updated_at")

        original_updated_at = container.updated_at

        import time
        time.sleep(0.01)

        container.iso_type = "42G1"
        container.save()

        assert container.updated_at > original_updated_at

    def test_container_iso_type_required(self):
        """Test that iso_type field is required."""
        container = Container(container_number="MSKU1234567")

        with pytest.raises(ValidationError) as exc_info:
            container.full_clean()

        assert "iso_type" in str(exc_info.value)

    def test_container_all_iso_types(self):
        """Test all available ISO type choices."""
        iso_types = [
            "22G1", "22K2", "25G1", "42G1", "45G1", "L5G1",
            "22R1", "42R1", "45R1", "L5R1",
            "22U1", "42U1", "45U1",
            "22P1", "42P1", "45P1",
            "22T1", "42T1",
        ]

        for i, iso_type in enumerate(iso_types):
            # Generate unique container numbers
            letter = chr(65 + (i % 26))  # A-Z
            container = Container.objects.create(
                container_number=f"{letter * 4}{str(i).zfill(7)}",
                iso_type=iso_type,
            )
            assert container.iso_type == iso_type
