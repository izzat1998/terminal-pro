import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.utils import safe_int_param
from apps.gate.models import ANPRDetection
from apps.gate.serializers import ANPRDetectionSerializer, ANPREventSerializer, PTZCommandSerializer
from apps.gate.services import HikvisionANPRService
from apps.gate.services.camera_control_service import CameraControlService


logger = logging.getLogger(__name__)


def _get_client_ip(request) -> str:
    """Extract client IP from REMOTE_ADDR.

    We intentionally do NOT trust X-Forwarded-For here because this endpoint
    uses AllowAny — a spoofed header would bypass IP whitelisting.
    In production, nginx sets REMOTE_ADDR to the real client IP.
    """
    return request.META.get("REMOTE_ADDR", "")


def _get_allowed_ips() -> set[str]:
    """Return the set of IPs allowed to call the ANPR webhook."""
    camera_ip = getattr(settings, "GATE_CAMERA_IP", "192.168.1.7")
    return {camera_ip, "127.0.0.1", "::1", "localhost"}


class ANPREventWebhookView(APIView):
    """Receive ANPR detection events via HTTP POST.

    Accepts webhook notifications from the Hikvision camera or any external
    system. Uses AllowAny permission with IP-based access control since the
    camera cannot send JWT.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Receive ANPR detection event",
        description="Webhook endpoint for Hikvision camera ANPR notifications. "
                    "Accepts plate detection data and processes through the ANPR pipeline.",
        request=ANPREventSerializer,
        responses={201: ANPRDetectionSerializer},
    )
    def post(self, request):
        client_ip = _get_client_ip(request)
        if client_ip not in _get_allowed_ips():
            logger.warning(f"ANPR webhook rejected from unauthorized IP: {client_ip}")
            return Response(
                {"success": False, "error": {"code": "UNAUTHORIZED_IP", "message": "Доступ запрещён"}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ANPREventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        gate_id = data.pop("gate_id", "main")

        service = HikvisionANPRService(
            camera_ip=getattr(settings, "GATE_CAMERA_IP", "192.168.1.7"),
            username="",
            password="",
            gate_id=gate_id,
        )
        detection = service.process_webhook_event(**data)

        if detection:
            return Response(
                {"success": True, "data": ANPRDetectionSerializer(detection).data},
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"success": True, "data": None, "message": "Событие обработано (возможно, дубликат)"},
            status=status.HTTP_200_OK,
        )


class ANPRDetectionListView(APIView):
    """List recent ANPR detections for a gate."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List recent ANPR detections",
        responses={200: ANPRDetectionSerializer(many=True)},
    )
    def get(self, request):
        gate_id = request.query_params.get("gate_id", "main")
        limit = safe_int_param(request.query_params.get("limit"), default=50, min_val=1, max_val=200)

        detections = ANPRDetection.objects.filter(gate_id=gate_id)[:limit]
        serializer = ANPRDetectionSerializer(detections, many=True)

        return Response({"success": True, "data": serializer.data})


class CameraPTZView(APIView):
    """Control gate camera PTZ (zoom in/out)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Send PTZ command to gate camera",
        description="Controls the Hikvision camera's motorized zoom lens. "
                    "Use zoom_in/zoom_out with continuous hold, then zoom_stop on release.",
        request=PTZCommandSerializer,
    )
    def post(self, request):
        serializer = PTZCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CameraControlService()
        service.send_ptz_command(
            action=serializer.validated_data["action"],
            speed=serializer.validated_data["speed"],
        )

        return Response({"success": True})
