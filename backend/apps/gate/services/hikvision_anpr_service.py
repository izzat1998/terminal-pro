import os
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import timedelta

import requests
from requests.auth import HTTPDigestAuth

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.core.exceptions import BusinessLogicError
from apps.core.services import BaseService
from apps.gate.models import ANPRDetection
from apps.gate.services.broadcast import broadcast_anpr_detection

# Reuse the vehicle type mapping from the existing PlateRecognizer service
from telegram_bot.services.plate_recognizer_service import map_vehicle_type


# Hikvision ISAPI XML namespace
NS = {"hik": "http://www.hikvision.com/ver20/XMLSchema"}

# Deduplication window in seconds
DEDUP_SECONDS = 5

# Minimum interval between PlateRecognizer captures (seconds)
CAPTURE_THROTTLE_SECONDS = 5


class HikvisionANPRService(BaseService):
    """Service for connecting to Hikvision ANPR camera and processing plate detections.

    Connects to the camera's ISAPI alertStream endpoint, parses XML events,
    deduplicates detections, saves to DB, auto-matches WAITING vehicles,
    and broadcasts via WebSocket.

    Supports two detection paths:
    1. Native ANPR: Camera sends <ANPR> XML with plate data (for cameras with built-in OCR)
    2. PlateRecognizer: On vehicledetection events, captures RTSP frame via ffmpeg,
       sends to PlateRecognizer API for Uzbek plate recognition
    """

    def __init__(
        self,
        camera_ip: str,
        username: str,
        password: str,
        gate_id: str = "main",
        camera_port: int = 80,
    ):
        super().__init__()
        self.camera_ip = camera_ip
        self.camera_port = camera_port
        self.username = username
        self.password = password
        self.gate_id = gate_id
        self.alert_stream_url = (
            f"http://{camera_ip}:{camera_port}/ISAPI/Event/notification/alertStream"
        )
        self._running = False
        self._last_capture_time: float = 0.0

    def listen(self) -> None:
        """Start listening to the camera alert stream with automatic reconnection."""
        self._running = True
        self._backoff = 3  # Initial backoff in seconds
        max_backoff = 30

        while self._running:
            try:
                self.logger.info(f"Connecting to ANPR camera at {self.camera_ip}...")
                self._stream_events()
            except requests.ConnectionError:
                self.logger.warning(f"Connection lost to {self.camera_ip}")
            except requests.Timeout:
                self.logger.warning(f"Connection timeout to {self.camera_ip}")
            except Exception:
                self.logger.exception("Unexpected error in ANPR stream")

            if not self._running:
                break

            self.logger.info(f"Reconnecting in {self._backoff}s...")
            time.sleep(self._backoff)
            self._backoff = min(self._backoff * 2, max_backoff)

    def stop(self) -> None:
        """Signal the listener to stop."""
        self._running = False

    def _stream_events(self) -> None:
        """Connect to camera and process events from the alert stream."""
        auth = HTTPDigestAuth(self.username, self.password)

        response = requests.get(
            self.alert_stream_url,
            auth=auth,
            stream=True,
            timeout=(10, None),  # 10s connect, no read timeout
        )
        response.raise_for_status()
        self.logger.info(f"Connected to ANPR camera at {self.camera_ip}")
        self._backoff = 3  # Reset backoff on successful connection

        buffer = ""
        for chunk in response.iter_content(chunk_size=1024):
            if not self._running:
                break

            if not chunk:
                continue

            buffer += chunk.decode("utf-8", errors="ignore")

            # Hikvision sends events separated by --boundary markers
            while "--boundary" in buffer:
                parts = buffer.split("--boundary", 1)
                event_xml = parts[0]
                buffer = parts[1] if len(parts) > 1 else ""

                if "<EventNotificationAlert" in event_xml:
                    self._handle_event_xml(event_xml)

    def _handle_event_xml(self, raw_xml: str) -> None:
        """Extract XML from multipart chunk and process it.

        Two detection paths:
        1. Native ANPR events (camera OCR): Parsed directly from <ANPR> XML
        2. vehicledetection events: Trigger ffmpeg capture → PlateRecognizer API
        """
        try:
            xml_start = raw_xml.index("<EventNotificationAlert")
            xml_end = raw_xml.index("</EventNotificationAlert>") + len(
                "</EventNotificationAlert>"
            )
            xml_text = raw_xml[xml_start:xml_end]
        except ValueError:
            return

        event_data = self._parse_event(xml_text)
        if not event_data:
            return

        # Path 1: Native ANPR with plate data from camera
        if event_data.get("plate_number"):
            self._process_detection(event_data)
            return

        # Path 2: vehicledetection → capture frame → PlateRecognizer
        if (
            event_data.get("event_type") == "vehicledetection"
            and event_data.get("event_state") == "active"
            and event_data.get("active_post_count") == "1"
        ):
            pr_data = self._capture_and_recognize()
            if pr_data:
                self._process_detection(pr_data)

    @staticmethod
    def _parse_event(xml_text: str) -> dict | None:
        """Parse a Hikvision EventNotificationAlert XML into a dict."""
        try:
            root = ET.fromstring(xml_text.strip())
        except ET.ParseError:
            return None

        event_type = root.findtext("hik:eventType", namespaces=NS) or ""
        date_time = root.findtext("hik:dateTime", namespaces=NS) or ""
        event_state = root.findtext("hik:eventState", namespaces=NS) or ""
        active_post_count = root.findtext("hik:activePostCount", namespaces=NS) or ""

        result = {
            "event_type": event_type,
            "datetime": date_time,
            "event_state": event_state,
            "active_post_count": active_post_count,
        }

        # Extract ANPR-specific data
        anpr = root.find("hik:ANPR", namespaces=NS)
        if anpr is not None:
            result["plate_number"] = (
                anpr.findtext("hik:licensePlate", namespaces=NS) or ""
            ).strip()
            result["confidence"] = (
                anpr.findtext("hik:confidenceLevel", namespaces=NS) or "0"
            )
            result["direction"] = (
                anpr.findtext("hik:direction", namespaces=NS) or "unknown"
            )
            result["country"] = anpr.findtext("hik:country", namespaces=NS) or ""
            result["plate_color"] = anpr.findtext("hik:plateColor", namespaces=NS) or ""
            result["vehicle_type"] = (
                anpr.findtext("hik:vehicleType", namespaces=NS) or ""
            )

        return result

    def _capture_and_recognize(self) -> dict | None:
        """Capture an RTSP frame via ffmpeg and send it to PlateRecognizer API.

        Returns a dict compatible with _process_detection() input, or None on failure.
        Throttled to at most one capture per CAPTURE_THROTTLE_SECONDS.
        """
        now = time.time()
        if now - self._last_capture_time < CAPTURE_THROTTLE_SECONDS:
            self.logger.debug("PlateRecognizer capture throttled")
            return None

        api_key = settings.PLATE_RECOGNIZER_API_KEY
        if not api_key:
            self.logger.warning("PLATE_RECOGNIZER_API_KEY not set — skipping capture")
            return None

        self._last_capture_time = now

        rtsp_url = (
            f"rtsp://{self.username}:{self.password}"
            f"@{self.camera_ip}:554/Streaming/Channels/101"
        )

        tmp_path = None
        try:
            # Capture a single RTSP frame to a temp JPEG file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-rtsp_transport",
                    "tcp",
                    "-i",
                    rtsp_url,
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    "-y",
                    "-update",
                    "1",
                    tmp_path,
                ],
                capture_output=True,
                timeout=10,
            )

            if result.returncode != 0:
                stderr_text = result.stderr.decode("utf-8", errors="ignore")[:200]
                stderr_safe = re.sub(r"rtsp://[^@]+@", "rtsp://***:***@", stderr_text)
                self.logger.error(
                    f"ffmpeg capture failed (rc={result.returncode}): {stderr_safe}"
                )
                return None

            file_size = os.path.getsize(tmp_path)
            if file_size < 1000:
                self.logger.warning(
                    f"Captured frame too small ({file_size} bytes) — likely blank"
                )
                return None

            # Send to PlateRecognizer API
            with open(tmp_path, "rb") as f:
                response = requests.post(
                    "https://api.platerecognizer.com/v1/plate-reader/",
                    files={"upload": ("frame.jpg", f, "image/jpeg")},
                    data={"regions": "uz"},
                    headers={"Authorization": f"Token {api_key}"},
                    timeout=10,
                )

            if response.status_code not in (200, 201):
                self.logger.error(
                    f"PlateRecognizer API error: {response.status_code} {response.text[:200]}"
                )
                return None

            data = response.json()
            results = data.get("results", [])
            if not results:
                self.logger.info("PlateRecognizer: no plates detected in frame")
                return None

            best = results[0]
            plate = (best.get("plate") or "").strip().upper()
            if not plate:
                return None

            score = best.get("score", 0.0)
            # Convert 0-1 float to 0-100 int for consistency with camera confidence
            confidence = int(score * 100)

            vehicle_data = best.get("vehicle", {})
            api_vehicle_type = vehicle_data.get("type")
            vehicle_type = map_vehicle_type(api_vehicle_type)

            self.logger.info(
                f"PlateRecognizer detected: {plate} ({confidence}%), "
                f"vehicle: {vehicle_type} (API: {api_vehicle_type})"
            )

            return {
                "plate_number": plate,
                "confidence": str(confidence),
                "direction": "approach",
                "vehicle_type": vehicle_type,
                "country": "uz",
                "plate_color": "",
                "event_type": "plate_recognizer",
                "datetime": timezone.now().isoformat(),
            }

        except subprocess.TimeoutExpired:
            self.logger.error("ffmpeg capture timed out")
            return None
        except requests.RequestException as exc:
            self.logger.error(f"PlateRecognizer request failed: {exc}")
            return None
        except Exception:
            self.logger.exception("Unexpected error in _capture_and_recognize")
            return None
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _process_detection(self, event_data: dict) -> ANPRDetection | None:
        """Process a single ANPR detection: deduplicate, save, match, broadcast.

        Returns the saved ANPRDetection, or None if deduplicated.
        """
        plate_number = event_data["plate_number"].upper().strip()
        if not plate_number:
            return None

        # Parse confidence safely
        try:
            confidence = int(event_data.get("confidence", 0))
        except (ValueError, TypeError):
            confidence = 0

        # Normalize direction
        direction_raw = (event_data.get("direction") or "unknown").lower()
        if direction_raw not in ("approach", "depart"):
            direction_raw = "unknown"

        # Parse camera timestamp
        camera_timestamp = None
        raw_dt = event_data.get("datetime", "")
        if raw_dt:
            camera_timestamp = parse_datetime(raw_dt)

        # Deduplication: skip if same plate detected within DEDUP_SECONDS
        cutoff = timezone.now() - timedelta(seconds=DEDUP_SECONDS)
        if ANPRDetection.objects.filter(
            plate_number=plate_number,
            gate_id=self.gate_id,
            created_at__gte=cutoff,
        ).exists():
            self.logger.debug(f"Duplicate detection skipped: {plate_number}")
            return None

        # Save to DB
        detection = ANPRDetection.objects.create(
            plate_number=plate_number,
            confidence=confidence,
            direction=direction_raw,
            vehicle_type=event_data.get("vehicle_type", ""),
            country=event_data.get("country", ""),
            plate_color=event_data.get("plate_color", ""),
            camera_timestamp=camera_timestamp,
            raw_event_type=event_data.get("event_type", ""),
            gate_id=self.gate_id,
        )

        self.logger.info(f"ANPR detection saved: {plate_number} ({confidence}%)")

        # Auto-match: find WAITING vehicle entry with this plate
        matched_entry = self._try_auto_match(plate_number, detection)

        # Broadcast via WebSocket
        broadcast_data = {
            "plate_number": plate_number,
            "confidence": confidence,
            "direction": direction_raw,
            "vehicle_type": event_data.get("vehicle_type", ""),
            "timestamp": (camera_timestamp or timezone.now()).isoformat(),
            "detection_id": detection.id,
            "event_type": "anpr",
            "matched_entry_id": matched_entry.id if matched_entry else None,
        }

        try:
            broadcast_anpr_detection(self.gate_id, broadcast_data)
        except Exception:
            self.logger.exception("Failed to broadcast ANPR detection")

        return detection

    def _try_auto_match(self, plate_number: str, detection: ANPRDetection):
        """Try to auto-match detection to a WAITING VehicleEntry and check it in.

        Returns the matched VehicleEntry or None.
        """
        from apps.vehicles.models import VehicleEntry

        waiting_entry = VehicleEntry.objects.filter(
            license_plate=plate_number,
            status="WAITING",
        ).first()

        if not waiting_entry:
            return None

        try:
            from apps.vehicles.services.vehicle_entry_service import VehicleEntryService

            service = VehicleEntryService()
            entry = service.check_in(
                license_plate=plate_number,
                entry_photos=[],
                recorded_by=None,
            )

            # Link detection to matched entry
            detection.matched_entry = entry
            detection.save(update_fields=["matched_entry"])

            self.logger.info(f"Auto-matched ANPR detection to VehicleEntry #{entry.id}")
            return entry

        except BusinessLogicError as exc:
            self.logger.warning(f"Auto-match rejected for {plate_number}: {exc}")
            return None
        except Exception:
            self.logger.exception(f"Failed to auto-match vehicle {plate_number}")
            return None

    def process_webhook_event(
        self, plate_number: str, confidence: int = 0, **kwargs
    ) -> ANPRDetection | None:
        """Process an ANPR event received via webhook (HTTP POST).

        Same pipeline as streaming events, triggered by an HTTP request.

        Returns:
            Saved ANPRDetection, or None if deduplicated.
        """
        event_data = {
            "plate_number": plate_number,
            "confidence": str(confidence),
            "direction": kwargs.get("direction", "unknown"),
            "vehicle_type": kwargs.get("vehicle_type", ""),
            "country": kwargs.get("country", ""),
            "plate_color": kwargs.get("plate_color", ""),
            "event_type": kwargs.get("event_type", "webhook"),
            "datetime": kwargs.get("camera_timestamp", ""),
        }
        return self._process_detection(event_data)
