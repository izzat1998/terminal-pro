"""
Generate draft monthly statements for all companies with activity.

Usage:
    python manage.py generate_monthly_statements           # Previous month
    python manage.py generate_monthly_statements 2026 1    # Specific month

Designed for cron: 0 2 1 * *
"""

from datetime import date

from django.core.management.base import BaseCommand

from apps.billing.services.statement_service import MonthlyStatementService


class Command(BaseCommand):
    help = "Generate draft monthly statements for all companies with container activity"

    def add_arguments(self, parser):
        parser.add_argument("year", nargs="?", type=int, help="Statement year")
        parser.add_argument("month", nargs="?", type=int, help="Statement month (1-12)")

    def handle(self, *args, **options):
        year = options.get("year")
        month = options.get("month")

        if not year or not month:
            # Default to previous month
            today = date.today()
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

        self.stdout.write(f"Generating draft statements for {year}/{month:02d}...")

        service = MonthlyStatementService()
        statements = service.generate_all_drafts(year, month)

        self.stdout.write(
            self.style.SUCCESS(f"Generated {len(statements)} draft statements")
        )
        for stmt in statements:
            self.stdout.write(f"  - {stmt.company.name}: ${stmt.total_usd}")
