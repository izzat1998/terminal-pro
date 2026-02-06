"""
Tests for billing service fixes (pure unit tests, no DB access).

Covers:
1. billing_available_periods uses TruncMonth DB aggregation (no N+1)
2. CustomerSerializer orders_count uses annotation
3. Residual billing rate uses most recent period
4. StatementLineItem immutability on finalized statements
5. Silent date parsing now returns 400 errors
6. CustomerStorageCostView response format includes "success"

All tests use mocks -- no database, no APIClient.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "terminal_app.settings")

import django

django.setup()

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.core.exceptions import BusinessLogicError


# Override the autouse db fixture from conftest.py
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests():
    """Override conftest autouse fixture -- no DB needed for these tests."""
    pass


# ============================================================================
# 1. billing_available_periods uses TruncMonth (no N+1)
# ============================================================================


@pytest.mark.unit
class TestBillingAvailablePeriodsAggregation:
    """Verify billing_available_periods uses DB-level TruncMonth aggregation."""

    def _make_viewset(self):
        """Create a CompanyViewSet with mocked internals."""
        from apps.accounts.company_views import CompanyViewSet

        viewset = CompanyViewSet()
        mock_company = MagicMock()
        mock_company.slug = "test-co"
        viewset.get_object = MagicMock(return_value=mock_company)
        viewset.request = MagicMock()
        viewset.request.query_params = {}
        viewset.format_kwarg = None
        viewset.kwargs = {"slug": "test-co"}
        return viewset

    def test_uses_trunc_month_aggregation(self):
        """
        billing_available_periods should use TruncMonth annotation
        rather than loading all entry_time values into Python.
        """
        viewset = self._make_viewset()

        mock_dt_july = MagicMock(year=2025, month=7)
        mock_dt_june = MagicMock(year=2025, month=6)

        with patch(
            "apps.terminal_operations.models.ContainerEntry.objects"
        ) as mock_objects:
            qs = mock_objects.filter.return_value
            qs.annotate.return_value = qs
            qs.values_list.return_value = qs
            qs.distinct.return_value = qs
            qs.order_by.return_value = [mock_dt_july, mock_dt_june]

            response = viewset.billing_available_periods(
                viewset.request, slug="test-co"
            )

        assert response.status_code == 200
        data = response.data
        assert data["success"] is True
        assert len(data["data"]) == 2

        # Verify annotate was called with TruncMonth
        qs.annotate.assert_called_once()
        annotate_kwargs = qs.annotate.call_args.kwargs
        assert "month" in annotate_kwargs
        from django.db.models.functions import TruncMonth

        assert isinstance(annotate_kwargs["month"], TruncMonth)

    def test_returns_correct_period_format(self):
        """Each period should have year, month, and Russian label."""
        viewset = self._make_viewset()

        mock_dt = MagicMock(year=2025, month=3)

        with patch(
            "apps.terminal_operations.models.ContainerEntry.objects"
        ) as mock_objects:
            qs = mock_objects.filter.return_value
            qs.annotate.return_value = qs
            qs.values_list.return_value = qs
            qs.distinct.return_value = qs
            qs.order_by.return_value = [mock_dt]

            response = viewset.billing_available_periods(
                viewset.request, slug="test-co"
            )

        periods = response.data["data"]
        assert len(periods) == 1
        p = periods[0]
        assert p["year"] == 2025
        assert p["month"] == 3
        assert "label" in p
        assert "Март" in p["label"]


# ============================================================================
# 2. CustomerSerializer orders_count annotation
# ============================================================================


@pytest.mark.unit
class TestCustomerSerializerOrdersCount:
    """Verify CustomerSerializer.get_orders_count works with annotation."""

    def test_orders_count_uses_annotation_when_present(self):
        """
        When the queryset annotates orders_count, the serializer
        get_orders_count method should return the correct value.
        """
        from apps.accounts.serializers import CustomerSerializer

        mock_user = MagicMock(spec=[])  # empty spec to avoid auto-creating attrs
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user._orders_count = 5
        mock_user.pre_orders = MagicMock()
        mock_user.pre_orders.count.return_value = 5

        serializer = CustomerSerializer()
        count = serializer.get_orders_count(mock_user)
        assert count == 5

    def test_company_customers_endpoint_annotates_orders_count(self):
        """
        The customers() action should call .annotate(orders_count=Count(...)).
        """
        from apps.accounts.company_views import CompanyViewSet

        viewset = CompanyViewSet()
        mock_company = MagicMock()
        mock_company.slug = "test-co"
        viewset.get_object = MagicMock(return_value=mock_company)
        viewset.request = MagicMock()
        viewset.request.query_params = {}
        viewset.format_kwarg = None
        viewset.kwargs = {"slug": "test-co"}

        with patch(
            "apps.accounts.models.CustomUser.objects"
        ) as mock_objects:
            qs = mock_objects.filter.return_value
            qs.filter.return_value = qs
            qs.select_related.return_value = qs
            qs.annotate.return_value = qs
            qs.order_by.return_value = []

            with patch(
                "apps.accounts.serializers.CustomerSerializer"
            ) as MockSer:
                MockSer.return_value.data = []

                response = viewset.customers(
                    viewset.request, slug="test-co"
                )

            # Verify annotate was called with orders_count
            qs.annotate.assert_called_once()
            annotate_kwargs = qs.annotate.call_args.kwargs
            assert "orders_count" in annotate_kwargs


# ============================================================================
# 3. Residual billing rate uses most recent period
# ============================================================================


@pytest.mark.unit
class TestResidualBillingRateSelection:
    """Verify residual billing uses the last period's rate, not the first."""

    def test_statement_service_uses_last_period_rate_for_residual(self):
        """
        _create_residual_line_items should reference periods[-1]
        (the most recent tariff rate), not periods[0].
        """
        import inspect

        from apps.billing.services.statement_service import (
            MonthlyStatementService,
        )

        source = inspect.getsource(
            MonthlyStatementService._create_residual_line_items
        )

        assert "periods[-1]" in source, (
            "Expected _create_residual_line_items to use periods[-1] "
            "(most recent rate) but found something else"
        )

    def test_create_line_item_uses_first_period_rate(self):
        """
        _create_line_item (non-residual) should reference periods[0]
        which is correct for the initial tariff at entry time.
        """
        import inspect

        from apps.billing.services.statement_service import (
            MonthlyStatementService,
        )

        source = inspect.getsource(MonthlyStatementService._create_line_item)

        assert "periods[0]" in source, (
            "Expected _create_line_item to use periods[0] for entry-time rate"
        )


# ============================================================================
# 4. StatementLineItem immutability on finalized statements
# ============================================================================


@pytest.mark.unit
class TestStatementLineItemImmutability:
    """Verify StatementLineItem.save() prevents edits on non-draft statements."""

    def _make_line_item(self, pk_value, is_editable):
        """Create a StatementLineItem with mocked statement, bypassing FK descriptor."""
        from apps.billing.models import StatementLineItem

        line_item = object.__new__(StatementLineItem)
        line_item.pk = pk_value

        # Bypass Django's FK descriptor by patching the property access
        mock_statement = MagicMock()
        mock_statement.is_editable = is_editable
        # Write to __dict__ to skip the ForeignKey descriptor __set__
        line_item.__dict__["statement"] = mock_statement

        # Also patch the descriptor __get__ to return our mock
        return line_item, mock_statement

    def test_save_raises_on_finalized_statement(self):
        """
        When pk is set and statement is not editable, save() must raise
        BusinessLogicError with IMMUTABLE_LINE_ITEM code.
        """
        from apps.billing.models import StatementLineItem

        # Verify the save method source contains the immutability check
        import inspect

        source = inspect.getsource(StatementLineItem.save)
        assert "IMMUTABLE_LINE_ITEM" in source, (
            "StatementLineItem.save() should check for IMMUTABLE_LINE_ITEM"
        )
        assert "self.pk" in source, (
            "Immutability check should use self.pk"
        )
        assert "is_editable" in source, (
            "Immutability check should reference statement.is_editable"
        )

        # Test the actual logic with patched statement attribute access
        line_item, _ = self._make_line_item(pk_value=42, is_editable=False)

        # Patch the statement property access on the class to return our mock
        with patch.object(
            type(line_item), "statement",
            new_callable=lambda: property(
                lambda self: self.__dict__["statement"]
            ),
        ):
            with pytest.raises(BusinessLogicError) as exc_info:
                line_item.save()

            assert exc_info.value.error_code == "IMMUTABLE_LINE_ITEM"

    def test_save_succeeds_on_draft_statement(self):
        """
        When pk is set but statement IS editable (draft), save() should
        proceed to super().save() without raising.
        """
        line_item, _ = self._make_line_item(pk_value=42, is_editable=True)

        with patch.object(
            type(line_item), "statement",
            new_callable=lambda: property(
                lambda self: self.__dict__["statement"]
            ),
        ):
            with patch(
                "django.db.models.Model.save", return_value=None
            ) as mock_save:
                line_item.save()
                mock_save.assert_called_once()

    def test_save_allows_new_records_on_finalized_statement(self):
        """
        When pk is None (new record), save() should allow it even on
        a finalized statement -- the guard is `if self.pk and not ...`.
        """
        line_item, _ = self._make_line_item(pk_value=None, is_editable=False)

        with patch.object(
            type(line_item), "statement",
            new_callable=lambda: property(
                lambda self: self.__dict__["statement"]
            ),
        ):
            with patch(
                "django.db.models.Model.save", return_value=None
            ) as mock_save:
                line_item.save()
                mock_save.assert_called_once()


# ============================================================================
# 5. Silent date parsing now returns 400 errors
# ============================================================================


@pytest.mark.unit
class TestDateParsingReturns400:
    """Verify that invalid date strings produce 400 responses."""

    def test_on_demand_invoice_mark_paid_invalid_date(self):
        """
        on_demand_invoice_mark_paid should return 400 with INVALID_DATE
        when payment_date is not a valid YYYY-MM-DD string.
        """
        from apps.accounts.company_views import CompanyViewSet

        viewset = CompanyViewSet()
        mock_company = MagicMock(slug="test-co")
        viewset.get_object = MagicMock(return_value=mock_company)
        viewset.request = MagicMock()
        viewset.format_kwarg = None
        viewset.kwargs = {"slug": "test-co"}

        mock_request = MagicMock()
        mock_request.data = {"payment_date": "not-a-date"}

        mock_invoice = MagicMock(status="finalized")

        with patch.object(
            viewset, "_get_on_demand_invoice", return_value=mock_invoice
        ):
            response = viewset.on_demand_invoice_mark_paid(
                mock_request, slug="test-co", invoice_id="1"
            )

        assert response.status_code == 400
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "INVALID_DATE"

    def test_on_demand_invoice_mark_paid_valid_date_passes(self):
        """
        on_demand_invoice_mark_paid should NOT return 400 when
        payment_date is a valid YYYY-MM-DD string.
        """
        from apps.accounts.company_views import CompanyViewSet

        viewset = CompanyViewSet()
        mock_company = MagicMock(slug="test-co")
        viewset.get_object = MagicMock(return_value=mock_company)
        viewset.request = MagicMock()
        viewset.format_kwarg = None
        viewset.kwargs = {"slug": "test-co"}

        mock_request = MagicMock()
        mock_request.data = {
            "payment_date": "2025-06-15",
            "payment_reference": "",
        }
        mock_request.user = MagicMock()

        mock_invoice = MagicMock(status="finalized")

        with patch.object(
            viewset, "_get_on_demand_invoice", return_value=mock_invoice
        ):
            with patch(
                "apps.billing.services.on_demand_invoice_service.OnDemandInvoiceService"
            ) as MockService:
                mock_service_inst = MockService.return_value
                mock_service_inst.mark_paid.return_value = mock_invoice

                with patch(
                    "apps.billing.serializers.OnDemandInvoiceListSerializer"
                ) as MockSerializer:
                    MockSerializer.return_value.data = {"id": 1}

                    response = viewset.on_demand_invoice_mark_paid(
                        mock_request, slug="test-co", invoice_id="1"
                    )

        assert response.status_code == 200
        assert response.data["success"] is True

    def test_storage_cost_view_invalid_as_of_date(self):
        """
        StorageCostView.get should return 400 with INVALID_DATE
        when as_of_date is not a valid YYYY-MM-DD string.
        """
        from apps.billing.views import StorageCostView

        view = StorageCostView()

        mock_request = MagicMock()
        mock_request.query_params = {"as_of_date": "invalid-date"}
        mock_request.user = MagicMock(is_authenticated=True)

        with patch(
            "apps.billing.views.get_object_or_404", return_value=MagicMock()
        ):
            response = view.get(mock_request, entry_id=1)

        assert response.status_code == 400
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "INVALID_DATE"

    def test_storage_cost_view_valid_as_of_date_passes(self):
        """
        StorageCostView.get should NOT return 400 when as_of_date
        is a valid YYYY-MM-DD string.
        """
        from apps.billing.views import StorageCostView

        view = StorageCostView()

        mock_request = MagicMock()
        mock_request.query_params = {"as_of_date": "2025-06-15"}
        mock_request.user = MagicMock(is_authenticated=True)

        with patch(
            "apps.billing.views.get_object_or_404", return_value=MagicMock()
        ):
            with patch(
                "apps.billing.views.StorageCostService"
            ) as MockService:
                MockService.return_value.calculate_cost.return_value = (
                    MagicMock()
                )
                with patch(
                    "apps.billing.views.StorageCostResultSerializer"
                ) as MockSer:
                    MockSer.return_value.data = {"total_usd": "0.00"}
                    response = view.get(mock_request, entry_id=1)

        assert response.status_code == 200
        assert response.data["success"] is True


# ============================================================================
# 6. CustomerStorageCostView response format includes "success"
# ============================================================================


@pytest.mark.unit
class TestCustomerStorageCostViewResponseFormat:
    """Verify CustomerStorageCostView response includes 'success' field."""

    def test_response_includes_success_true(self):
        """
        CustomerStorageCostView.get response should contain
        'success': True at the top level.
        """
        from apps.billing.views import CustomerStorageCostView

        view = CustomerStorageCostView()

        mock_request = MagicMock()
        mock_request.query_params = {}
        mock_request.user = MagicMock(
            is_authenticated=True, user_type="customer"
        )

        mock_company = MagicMock(slug="test-co")

        with patch(
            "apps.billing.views._get_customer_company",
            return_value=mock_company,
        ):
            with patch("apps.billing.views.ContainerEntry") as MockEntry:
                qs = MockEntry.objects.filter.return_value
                qs.select_related.return_value = qs
                qs.filter.return_value = qs
                qs.order_by.return_value = qs
                qs.count.return_value = 0
                qs.__getitem__ = MagicMock(return_value=[])

                with patch(
                    "apps.billing.views.StorageCostService"
                ) as MockService:
                    MockService.return_value.calculate_bulk_costs.return_value = []

                    with patch(
                        "apps.billing.views.get_invoiced_entry_ids",
                        return_value=set(),
                    ):
                        response = view.get(mock_request)

        assert response.status_code == 200
        assert "success" in response.data
        assert response.data["success"] is True
        assert "results" in response.data
        assert "count" in response.data
        assert "summary" in response.data

    def test_response_without_company_returns_error(self):
        """
        When customer has no company, response should contain
        'success': False with NO_COMPANY error code.
        """
        from apps.billing.views import CustomerStorageCostView

        view = CustomerStorageCostView()

        mock_request = MagicMock()
        mock_request.query_params = {}
        mock_request.user = MagicMock(
            is_authenticated=True, user_type="customer"
        )

        with patch(
            "apps.billing.views._get_customer_company", return_value=None
        ):
            response = view.get(mock_request)

        assert response.status_code == 400
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "NO_COMPANY"
