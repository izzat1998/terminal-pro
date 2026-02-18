import signal
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.gate.services import HikvisionANPRService


class Command(BaseCommand):
    help = (
        "Test ANPR pipeline: capture RTSP frames in a loop → PlateRecognizer → "
        "webhook → WebSocket → 3D animation"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=10,
            help="Seconds between captures (default: 10)",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=0,
            help="Max captures, 0 = infinite (default: 0)",
        )
        parser.add_argument(
            "--gate-id",
            default="main",
            help="Gate identifier for webhook (default: main)",
        )
        parser.add_argument(
            "--camera-ip",
            default=None,
            help="Camera IP address (overrides GATE_CAMERA_IP env var)",
        )
        parser.add_argument(
            "--camera-user",
            default=None,
            help="Camera username (overrides GATE_CAMERA_USER env var)",
        )
        parser.add_argument(
            "--camera-pass",
            default=None,
            help="Camera password (overrides GATE_CAMERA_PASS env var)",
        )
        parser.add_argument(
            "--webhook-url",
            default="http://localhost:8008/api/gate/anpr-event/",
            help="Webhook endpoint URL (default: http://localhost:8008/api/gate/anpr-event/)",
        )

    def handle(self, *args, **options):
        camera_ip = options["camera_ip"] or getattr(settings, "GATE_CAMERA_IP", "192.168.1.7")
        camera_user = options["camera_user"] or getattr(settings, "GATE_CAMERA_USER", "admin")
        camera_pass = options["camera_pass"] or getattr(settings, "GATE_CAMERA_PASS", "")
        gate_id = options["gate_id"]
        interval = options["interval"]
        count = options["count"]
        webhook_url = options["webhook_url"]

        if not camera_pass:
            self.stderr.write(self.style.ERROR(
                "Camera password not set. Set GATE_CAMERA_PASS in .env or use --camera-pass."
            ))
            return

        service = HikvisionANPRService(
            camera_ip=camera_ip,
            username=camera_user,
            password=camera_pass,
            gate_id=gate_id,
        )

        # Graceful shutdown on SIGINT/SIGTERM
        running = True

        def shutdown_handler(signum, frame):
            nonlocal running
            self.stdout.write("\nShutting down test capture loop...")
            running = False

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        count_label = str(count) if count else "∞"
        self.stdout.write(self.style.SUCCESS(
            f"Starting ANPR test capture loop: camera={camera_ip}, "
            f"interval={interval}s, count={count_label}"
        ))

        iteration = 0
        while running:
            iteration += 1
            if count and iteration > count:
                break

            prefix = f"[{iteration}/{count_label}]"

            # Bypass the 5-second capture throttle
            service._last_capture_time = 0

            result = service._capture_and_recognize()
            if not result:
                self.stdout.write(f"{prefix} No plate detected in frame")
            else:
                plate = result["plate_number"]
                confidence = result["confidence"]
                vehicle_type = result.get("vehicle_type", "")
                self.stdout.write(
                    f"{prefix} Captured frame → PlateRecognizer: "
                    f"{plate} ({confidence}%) {vehicle_type}"
                )

                # POST to webhook so detection flows through the Django server process
                # where WebSocket clients are connected
                payload = {
                    "plate_number": plate,
                    "confidence": int(confidence),
                    "direction": result.get("direction", "approach"),
                    "vehicle_type": vehicle_type,
                    "gate_id": gate_id,
                }
                try:
                    resp = requests.post(webhook_url, json=payload, timeout=5)
                    self.stdout.write(
                        f"{prefix} Webhook response: {resp.status_code} "
                        f"{resp.reason}"
                    )
                except requests.RequestException as exc:
                    self.stderr.write(self.style.ERROR(
                        f"{prefix} Webhook POST failed: {exc}"
                    ))

            # Sleep in small increments so SIGINT is responsive
            for _ in range(interval * 10):
                if not running:
                    break
                time.sleep(0.1)

        self.stdout.write(self.style.SUCCESS(
            f"Test capture loop stopped after {iteration - 1} capture(s)."
        ))
