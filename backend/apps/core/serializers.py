from rest_framework import serializers

from apps.core.models import TelegramActivityLog


class TelegramActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for TelegramActivityLog with user and action details."""

    user_full_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    user_type_display = serializers.CharField(
        source="get_user_type_display", read_only=True
    )
    related_object_str = serializers.SerializerMethodField()

    class Meta:
        model = TelegramActivityLog
        fields = [
            "id",
            "user",
            "user_full_name",
            "user_type",
            "user_type_display",
            "telegram_user_id",
            "action",
            "action_display",
            "details",
            "success",
            "error_message",
            "related_object_str",
            "created_at",
        ]
        read_only_fields = fields

    def get_user_full_name(self, obj):
        """Get the full name of the user who performed the action."""
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None

    def get_related_object_str(self, obj):
        """Get a string representation of the related object."""
        if obj.content_object:
            return str(obj.content_object)
        return None


class TelegramActivityLogStatsSerializer(serializers.Serializer):
    """Serializer for activity statistics."""

    action = serializers.CharField()
    action_display = serializers.CharField()
    count = serializers.IntegerField()


class TelegramActivityLogSummarySerializer(serializers.Serializer):
    """Serializer for activity summary response."""

    total_count = serializers.IntegerField()
    success_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
    by_action = TelegramActivityLogStatsSerializer(many=True)
    by_user_type = serializers.DictField()
