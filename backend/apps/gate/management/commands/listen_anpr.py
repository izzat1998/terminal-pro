import signal

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.gate.services import HikvisionANPRService


class Command(BaseCommand):
    help = "Listen for ANPR events from the Hikvision gate camera and process them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--gate-id",
            default="main",
            help="Gate identifier for WebSocket broadcasting (default: main)",
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

    def handle(self, *args, **options):
        camera_ip = options["camera_ip"] or getattr(
            settings, "GATE_CAMERA_IP", "192.168.1.7"
        )
        camera_port = getattr(settings, "GATE_CAMERA_PORT", 80)
        camera_user = options["camera_user"] or getattr(
            settings, "GATE_CAMERA_USER", "admin"
        )
        camera_pass = options["camera_pass"] or getattr(
            settings, "GATE_CAMERA_PASS", ""
        )
        gate_id = options["gate_id"]

        if not camera_pass:
            self.stderr.write(
                self.style.ERROR(
                    "Camera password not set. Set GATE_CAMERA_PASS in .env or use --camera-pass."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting ANPR listener: camera={camera_ip}:{camera_port}, gate={gate_id}"
            )
        )

        service = HikvisionANPRService(
            camera_ip=camera_ip,
            username=camera_user,
            password=camera_pass,
            gate_id=gate_id,
            camera_port=camera_port,
        )

        # Graceful shutdown on SIGINT/SIGTERM
        def shutdown_handler(signum, frame):
            self.stdout.write("\nShutting down ANPR listener...")
            service.stop()

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        service.listen()

        self.stdout.write(self.style.SUCCESS("ANPR listener stopped."))
