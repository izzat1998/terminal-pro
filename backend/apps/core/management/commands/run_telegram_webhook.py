"""
Django management command to run the Telegram bot in webhook mode.

Usage:
    python manage.py run_telegram_webhook

This starts an aiohttp server that receives webhook requests from Telegram.
For local development, use polling mode instead: python manage.py run_telegram_bot
"""

import asyncio
import os
import sys

from django.core.management.base import BaseCommand


# Add telegram_bot to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


class Command(BaseCommand):
    help = "Run the Telegram bot in webhook mode (production)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--port",
            type=int,
            default=None,
            help="Port to listen on (default: from settings or 8001)",
        )
        parser.add_argument(
            "--host",
            type=str,
            default=None,
            help="Host to bind to (default: 0.0.0.0)",
        )

    def handle(self, *args, **options):
        # Override port/host if provided via command line
        if options["port"]:
            os.environ["TELEGRAM_WEBHOOK_PORT"] = str(options["port"])
        if options["host"]:
            os.environ["TELEGRAM_WEBHOOK_HOST"] = options["host"]

        self.stdout.write(
            self.style.SUCCESS("Starting Telegram bot in webhook mode...")
        )

        try:
            from telegram_bot.webhook import main

            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nWebhook server stopped by user"))
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"Configuration error: {e}"))
            self.stdout.write(
                self.style.WARNING(
                    "For local development, use polling mode: python manage.py run_telegram_bot"
                )
            )
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running webhook server: {e}"))
            raise
