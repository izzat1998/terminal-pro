import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


logger = logging.getLogger(__name__)


class GateConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for gate camera real-time events."""

    room_group_name: str | None = None

    async def connect(self) -> None:
        """Handle WebSocket connection. Requires JWT authentication via query string."""
        user = self.scope.get("user", AnonymousUser())
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            logger.warning("WebSocket connection rejected: unauthenticated")
            await self.close()
            return

        self.gate_id = self.scope["url_route"]["kwargs"].get("gate_id", "main")
        self.room_group_name = f"gate_{self.gate_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info(f"WebSocket connected: gate_id={self.gate_id}, user={user.username}")

    async def disconnect(self, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.info(f"WebSocket disconnected: gate_id={self.gate_id}, code={close_code}")

    async def vehicle_detected(self, event: dict) -> None:
        """Send vehicle detection to WebSocket clients."""
        await self.send_json(event["data"])

    async def anpr_detection(self, event: dict) -> None:
        """Send ANPR detection to WebSocket clients."""
        await self.send_json(event["data"])
