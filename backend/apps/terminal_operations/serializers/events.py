"""
Serializers for container event tracking.
"""

from rest_framework import serializers

from ..models import ContainerEvent


class EventPerformerSerializer(serializers.Serializer):
    """Nested serializer for the user who performed the action."""
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()
    user_type = serializers.CharField()

    def get_full_name(self, obj):
        return obj.full_name or obj.username


class ContainerEventSerializer(serializers.ModelSerializer):
    """
    Serializer for ContainerEvent model.
    Returns event data with display labels for UI rendering.
    """

    event_type_display = serializers.CharField(
        source="get_event_type_display",
        read_only=True,
    )
    source_display = serializers.CharField(
        source="get_source_display",
        read_only=True,
    )
    performed_by = EventPerformerSerializer(read_only=True)

    class Meta:
        model = ContainerEvent
        fields = [
            "id",
            "event_type",
            "event_type_display",
            "event_time",
            "performed_by",
            "source",
            "source_display",
            "details",
            "created_at",
        ]
        read_only_fields = fields


class ContainerTimelineSerializer(serializers.Serializer):
    """
    Serializer for container timeline response.
    Wraps events with container context.
    """

    container_number = serializers.CharField()
    container_entry_id = serializers.IntegerField()
    events = ContainerEventSerializer(many=True)
