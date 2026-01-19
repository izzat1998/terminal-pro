import pytest
from datetime import date
from decimal import Decimal

from apps.accounts.models import Company
from apps.billing.models import MonthlyStatement, StatementLineItem


@pytest.mark.django_db
class TestMonthlyStatementModel:
    def test_create_monthly_statement(self):
        """MonthlyStatement should be created with required fields."""
        company = Company.objects.create(name="Test Company")
        statement = MonthlyStatement.objects.create(
            company=company,
            year=2026,
            month=1,
            billing_method="split",
            total_containers=5,
            total_billable_days=45,
            total_usd=Decimal("500.00"),
            total_uzs=Decimal("6500000.00"),
        )
        assert statement.id is not None
        assert statement.company == company
        assert statement.year == 2026
        assert statement.month == 1
        assert statement.month_name == "Январь"

    def test_monthly_statement_unique_constraint(self):
        """Only one statement per company per month."""
        company = Company.objects.create(name="Test Company")
        MonthlyStatement.objects.create(
            company=company, year=2026, month=1, billing_method="split"
        )
        with pytest.raises(Exception):  # IntegrityError
            MonthlyStatement.objects.create(
                company=company, year=2026, month=1, billing_method="split"
            )


@pytest.mark.django_db
class TestStatementLineItemModel:
    def test_create_statement_line_item(self):
        """StatementLineItem should be created with required fields."""
        company = Company.objects.create(name="Test Company")
        statement = MonthlyStatement.objects.create(
            company=company, year=2026, month=1, billing_method="split"
        )
        line_item = StatementLineItem.objects.create(
            statement=statement,
            container_number="HDMU1234567",
            container_size="40ft",
            container_status="laden",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 15),
            total_days=15,
            free_days=3,
            billable_days=12,
            daily_rate_usd=Decimal("15.00"),
            daily_rate_uzs=Decimal("195000.00"),
            amount_usd=Decimal("180.00"),
            amount_uzs=Decimal("2340000.00"),
        )
        assert line_item.id is not None
        assert line_item.statement == statement
