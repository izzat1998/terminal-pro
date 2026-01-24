import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


logger = logging.getLogger(__name__)


def broadcast_vehicle_detection(gate_id: str, detection_data: dict) -> None:
    """Broadcast vehicle detection to all connected WebSocket clients.

    Args:
        gate_id: The gate identifier (e.g., "main", "entry", "exit")
        detection_data: Detection event data to broadcast
    """
    channel_layer = get_channel_layer()
    group_name = f"gate_{gate_id}"

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "vehicle_detected",
            "data": detection_data,
        },
    )

    logger.info(f"Broadcast vehicle detection to {group_name}")
