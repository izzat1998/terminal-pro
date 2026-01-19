import pytest
from apps.accounts.models import Company


@pytest.mark.django_db
class TestCompanyBillingMethod:
    def test_company_has_billing_method_field(self):
        """Company should have billing_method field with default 'split'."""
        company = Company.objects.create(name="Test Company")
        assert hasattr(company, "billing_method")
        assert company.billing_method == "split"

    def test_company_billing_method_choices(self):
        """Company billing_method should accept 'split' and 'exit_month'."""
        company = Company.objects.create(name="Test Company", billing_method="exit_month")
        assert company.billing_method == "exit_month"

        company.billing_method = "split"
        company.save()
        company.refresh_from_db()
        assert company.billing_method == "split"
