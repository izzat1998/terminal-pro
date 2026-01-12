"""
Django management command to run the Telegram bot
"""

import asyncio
import os
import sys

from django.core.management.base import BaseCommand


# Add telegram_bot to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


class Command(BaseCommand):
    help = "Run the Telegram bot for container entry management"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Telegram bot..."))

        try:
            from telegram_bot.bot import main

            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nBot stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running bot: {e}"))
            raise
