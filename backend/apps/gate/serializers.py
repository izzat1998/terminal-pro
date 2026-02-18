from rest_framework import serializers

from apps.gate.models import ANPRDetection


class ANPREventSerializer(serializers.Serializer):
    """Serializer for incoming ANPR webhook events."""

    plate_number = serializers.CharField(max_length=20)
    confidence = serializers.IntegerField(default=0, min_value=0, max_value=100)
    direction = serializers.ChoiceField(
        choices=["approach", "depart", "unknown"],
        default="unknown",
    )
    vehicle_type = serializers.CharField(max_length=50, default="", required=False, allow_blank=True)
    country = serializers.CharField(max_length=10, default="", required=False, allow_blank=True)
    plate_color = serializers.CharField(max_length=20, default="", required=False, allow_blank=True)
    camera_timestamp = serializers.DateTimeField(required=False, allow_null=True)
    gate_id = serializers.CharField(max_length=50, default="main", required=False)


class PTZCommandSerializer(serializers.Serializer):
    """Serializer for PTZ camera control commands."""

    action = serializers.ChoiceField(choices=["zoom_in", "zoom_out", "zoom_stop"])
    speed = serializers.IntegerField(default=50, min_value=1, max_value=100)


class ANPRDetectionSerializer(serializers.ModelSerializer):
    """Read-only serializer for ANPR detection records."""

    class Meta:
        model = ANPRDetection
        fields = [
            "id",
            "plate_number",
            "confidence",
            "direction",
            "vehicle_type",
            "country",
            "plate_color",
            "camera_timestamp",
            "raw_event_type",
            "matched_entry",
            "gate_id",
            "created_at",
        ]
        read_only_fields = fields
