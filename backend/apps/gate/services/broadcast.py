import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


logger = logging.getLogger(__name__)


def _broadcast(gate_id: str, message_type: str, data: dict) -> None:
    """Send a message to all WebSocket clients subscribed to a gate group."""
    channel_layer = get_channel_layer()
    group_name = f"gate_{gate_id}"

    async_to_sync(channel_layer.group_send)(
        group_name,
        {"type": message_type, "data": data},
    )

    plate = data.get("plate_number", "")
    logger.info(f"Broadcast {message_type} to {group_name}" + (f": {plate}" if plate else ""))


def broadcast_vehicle_detection(gate_id: str, detection_data: dict) -> None:
    """Broadcast vehicle detection to all connected WebSocket clients."""
    _broadcast(gate_id, "vehicle_detected", detection_data)


def broadcast_anpr_detection(gate_id: str, detection_data: dict) -> None:
    """Broadcast ANPR detection event to all connected WebSocket clients."""
    detection_data.setdefault("event_type", "anpr")
    _broadcast(gate_id, "anpr_detection", detection_data)
