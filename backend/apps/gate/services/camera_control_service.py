import requests
from requests.auth import HTTPDigestAuth

from django.conf import settings

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService


# Hikvision ISAPI PTZ continuous control XML template
PTZ_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<PTZData>
  <pan>0</pan>
  <tilt>0</tilt>
  <zoom>{zoom}</zoom>
</PTZData>"""

# Valid PTZ actions and their zoom values
PTZ_ACTIONS = {
    "zoom_in": lambda speed: speed,
    "zoom_out": lambda speed: -speed,
    "zoom_stop": lambda _: 0,
}


class CameraControlService(BaseService):
    """Service for controlling the Hikvision gate camera via ISAPI."""

    def __init__(self):
        super().__init__()
        self.camera_ip = getattr(settings, "GATE_CAMERA_IP", "192.168.1.7")
        self.camera_port = getattr(settings, "GATE_CAMERA_PORT", 80)
        self.username = getattr(settings, "GATE_CAMERA_USER", "admin")
        self.password = getattr(settings, "GATE_CAMERA_PASS", "")
        self.ptz_url = f"http://{self.camera_ip}:{self.camera_port}/ISAPI/PTZCtrl/channels/1/continuous"

    def send_ptz_command(self, action: str, speed: int = 50) -> None:
        """Send a PTZ continuous command to the camera.

        Args:
            action: One of 'zoom_in', 'zoom_out', 'zoom_stop'
            speed: Zoom speed 1-100 (ignored for zoom_stop)
        """
        if action not in PTZ_ACTIONS:
            raise BusinessLogicError(
                "Неизвестная команда PTZ",
                error_code="INVALID_PTZ_ACTION",
            )

        zoom_value = PTZ_ACTIONS[action](speed)
        xml_body = PTZ_XML_TEMPLATE.format(zoom=zoom_value)

        try:
            response = requests.put(
                self.ptz_url,
                data=xml_body,
                auth=HTTPDigestAuth(self.username, self.password),
                headers={"Content-Type": "application/xml"},
                timeout=5,
            )
            response.raise_for_status()
            self.logger.info(f"PTZ command sent: {action} (speed={speed})")
        except requests.ConnectionError:
            self.logger.error(f"Cannot connect to camera at {self.camera_ip}")
            raise BusinessLogicError(
                "Камера недоступна",
                error_code="CAMERA_UNREACHABLE",
            )
        except requests.Timeout:
            self.logger.error(f"Camera request timed out: {self.camera_ip}")
            raise BusinessLogicError(
                "Камера не отвечает",
                error_code="CAMERA_TIMEOUT",
            )
        except requests.HTTPError as exc:
            self.logger.error(f"Camera returned error: {exc.response.status_code}")
            raise BusinessLogicError(
                "Ошибка управления камерой",
                error_code="CAMERA_ERROR",
            )
