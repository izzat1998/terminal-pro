import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import TimestampedModel


User = get_user_model()


@pytest.mark.django_db
class TestTimestampedModel:
    def test_timestamps_are_set_on_creation(self):
        user = User.objects.create_user(username="testuser", password="testpass123")

        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at <= timezone.now()
        assert user.updated_at <= timezone.now()

    def test_updated_at_changes_on_save(self):
        user = User.objects.create_user(username="testuser", password="testpass123")

        original_updated_at = user.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        user.email = "new@example.com"
        user.save()

        assert user.updated_at > original_updated_at

    def test_created_at_does_not_change_on_save(self):
        user = User.objects.create_user(username="testuser", password="testpass123")

        original_created_at = user.created_at

        user.email = "new@example.com"
        user.save()

        assert user.created_at == original_created_at

    def test_timestamp_model_inheritance(self):
        # Test that TimestampedModel is properly inherited
        user = User()
        assert hasattr(user, "created_at")
        assert hasattr(user, "updated_at")
        assert isinstance(user, TimestampedModel)
