"""
Base and shared serializers for terminal operations.

Contains common nested serializers used across multiple domain serializers.
"""

from rest_framework import serializers

from apps.containers.models import Container

from ..models import ContainerOwner, CraneOperation


class ContainerOwnerSerializer(serializers.ModelSerializer):
    """
    Serializer for ContainerOwner model
    """

    class Meta:
        model = ContainerOwner
        fields = [
            "id",
            "name",
            "slug",
            "telegram_group_id",
            "telegram_group_name",
            "notifications_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "slug": {"required": False},  # Auto-generated if not provided
            "telegram_group_id": {"required": False, "allow_null": True},
            "telegram_group_name": {"required": False},
            "notifications_enabled": {"required": False},
        }

    def validate_name(self, value):
        """Validate name uniqueness on update"""
        if (
            self.instance
            and ContainerOwner.objects.filter(name=value)
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise serializers.ValidationError(
                "Владелец контейнера с таким именем уже существует"
            )
        return value

    def validate_slug(self, value):
        """Validate slug uniqueness on update"""
        if (
            value
            and self.instance
            and ContainerOwner.objects.filter(slug=value)
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise serializers.ValidationError(
                "Владелец контейнера с таким slug уже существует"
            )
        return value


class ContainerNestedSerializer(serializers.ModelSerializer):
    """
    Nested serializer for Container model (read-only, for FK representation)
    """

    class Meta:
        model = Container
        fields = ["id", "container_number", "iso_type"]
        read_only_fields = fields


class UserNestedSerializer(serializers.Serializer):
    """
    Nested serializer for User (recorded_by) - read-only representation
    """

    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class CraneOperationSerializer(serializers.ModelSerializer):
    """
    Serializer for CraneOperation model (read-only)
    """

    class Meta:
        model = CraneOperation
        fields = ["id", "operation_date", "created_at"]
        read_only_fields = ["id", "created_at"]


class CraneOperationWriteSerializer(serializers.Serializer):
    """
    Serializer for writing crane operations (used when creating/updating entries)
    Accepts just operation_date without container_entry_id
    """

    operation_date = serializers.DateTimeField()
