"""
Tests for security fixes applied to the MTT project.

All tests are pure unit tests -- no database access required.

Covers:
1. RegisterSerializer is_admin read_only enforcement
2. IsCustomer permission on customer billing view classes
3. safe_int_param utility (graceful handling of non-numeric input)
4. Production security headers in settings.py source
"""

import ast
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from apps.accounts.serializers import RegisterSerializer
from apps.billing.views import (
    CustomerBulkStorageCostView,
    CustomerStorageCostExportView,
    CustomerStorageCostView,
    CustomerStatementView,
    CustomerStatementListView,
    CustomerAvailablePeriodsView,
    CustomerStatementExportExcelView,
    CustomerStatementExportPdfView,
    CustomerAdditionalChargeView,
)
from apps.core.utils import safe_int_param
from apps.customer_portal.permissions import IsCustomer


# ============================================================================
# 1. RegisterSerializer is_admin read_only
# ============================================================================


@pytest.mark.unit
class TestRegisterSerializerIsAdminReadOnly:
    """Ensure is_admin cannot be set via the RegisterSerializer."""

    def test_is_admin_in_read_only_fields(self):
        """RegisterSerializer.Meta.read_only_fields must contain 'is_admin'."""
        assert "is_admin" in RegisterSerializer.Meta.read_only_fields

    def test_is_admin_listed_in_fields(self):
        """is_admin should be declared in fields so DRF enforces read_only."""
        assert "is_admin" in RegisterSerializer.Meta.fields

    def test_serializer_ignores_is_admin_in_input(self):
        """When is_admin=True is passed as input data, the serializer drops it."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepass123",
            "password_confirm": "securepass123",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
        }
        serializer = RegisterSerializer(data=data)
        # is_valid triggers validation; we only need to confirm the validated
        # data does NOT contain is_admin (DRF strips read_only fields).
        serializer.is_valid()
        assert "is_admin" not in serializer.validated_data


# ============================================================================
# 2. IsCustomer permission on billing views
# ============================================================================


@pytest.mark.unit
class TestIsCustomerPermissionOnBillingViews:
    """
    Verify that all customer billing views declare [IsAuthenticated, IsCustomer]
    in their permission_classes, which blocks admin and manager users.
    """

    # All customer-facing billing views that must enforce IsCustomer
    CUSTOMER_BILLING_VIEWS = [
        CustomerBulkStorageCostView,
        CustomerStorageCostView,
        CustomerStorageCostExportView,
        CustomerStatementView,
        CustomerStatementListView,
        CustomerAvailablePeriodsView,
        CustomerStatementExportExcelView,
        CustomerStatementExportPdfView,
        CustomerAdditionalChargeView,
    ]

    @pytest.mark.parametrize(
        "view_class",
        CUSTOMER_BILLING_VIEWS,
        ids=lambda cls: cls.__name__,
    )
    def test_view_has_is_customer_permission(self, view_class):
        """Each customer billing view must include IsCustomer in permission_classes."""
        assert IsCustomer in view_class.permission_classes, (
            f"{view_class.__name__}.permission_classes must include IsCustomer"
        )

    def test_is_customer_denies_admin_user(self):
        """IsCustomer.has_permission returns False for admin user_type."""
        user = MagicMock()
        user.is_authenticated = True
        user.user_type = "admin"
        request = MagicMock()
        request.user = user

        permission = IsCustomer()
        assert permission.has_permission(request, None) is False

    def test_is_customer_denies_manager_user(self):
        """IsCustomer.has_permission returns False for manager user_type."""
        user = MagicMock()
        user.is_authenticated = True
        user.user_type = "manager"
        request = MagicMock()
        request.user = user

        permission = IsCustomer()
        assert permission.has_permission(request, None) is False

    def test_is_customer_allows_customer_user(self):
        """IsCustomer.has_permission returns True for customer user_type."""
        user = MagicMock()
        user.is_authenticated = True
        user.user_type = "customer"
        request = MagicMock()
        request.user = user

        permission = IsCustomer()
        assert permission.has_permission(request, None) is True

    def test_is_customer_denies_anonymous(self):
        """IsCustomer.has_permission returns False for anonymous users."""
        user = MagicMock()
        user.is_authenticated = False
        request = MagicMock()
        request.user = user

        permission = IsCustomer()
        assert permission.has_permission(request, None) is False


# ============================================================================
# 3. safe_int_param on pagination
# ============================================================================


@pytest.mark.unit
class TestSafeIntParam:
    """Test the safe_int_param utility handles non-numeric values gracefully."""

    def test_valid_integer_string(self):
        assert safe_int_param("5", 1) == 5

    def test_non_numeric_returns_default(self):
        """'abc' should not cause a 500 -- returns default instead."""
        assert safe_int_param("abc", 1) == 1

    def test_none_returns_default(self):
        assert safe_int_param(None, 42) == 42

    def test_empty_string_returns_default(self):
        assert safe_int_param("", 10) == 10

    def test_float_string_returns_default(self):
        """'3.14' is not a valid int, so default is returned."""
        assert safe_int_param("3.14", 1) == 1

    def test_min_val_clamping(self):
        """Value below min_val is clamped up."""
        assert safe_int_param("-5", 1, min_val=1) == 1

    def test_max_val_clamping(self):
        """Value above max_val is clamped down."""
        assert safe_int_param("999", 1, max_val=100) == 100

    def test_min_and_max_together(self):
        """Both min and max constraints applied correctly."""
        assert safe_int_param("50", 1, min_val=1, max_val=100) == 50

    def test_negative_valid(self):
        """Negative integers parse correctly when no min_val set."""
        assert safe_int_param("-10", 0) == -10

    def test_zero(self):
        assert safe_int_param("0", 5) == 0


# ============================================================================
# 4. Production security headers (AST-based verification)
# ============================================================================


@pytest.mark.unit
class TestProductionSecurityHeaders:
    """
    Verify production security settings exist in settings.py.

    Since settings.py uses module-level `if not DEBUG:` to set these,
    and tests run with DEBUG=True, we parse the source AST to confirm
    the production code path sets the correct values.
    """

    SETTINGS_PATH = Path(__file__).resolve().parent.parent / "terminal_app" / "settings.py"

    @classmethod
    def _get_production_guard_assignments(cls):
        """
        Parse settings.py AST and extract all assignments inside
        `if not DEBUG:` blocks. Returns a dict of {name: ast_node}.
        """
        source = cls.SETTINGS_PATH.read_text()
        tree = ast.parse(source)

        assignments = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Match `if not DEBUG:`
                test = node.test
                if (
                    isinstance(test, ast.UnaryOp)
                    and isinstance(test.op, ast.Not)
                    and isinstance(test.operand, ast.Name)
                    and test.operand.id == "DEBUG"
                ):
                    for child in node.body:
                        if isinstance(child, ast.Assign):
                            for target in child.targets:
                                if isinstance(target, ast.Name):
                                    assignments[target.id] = child.value
        return assignments

    def test_hsts_seconds_set(self):
        """SECURE_HSTS_SECONDS = 31536000 in the 'if not DEBUG' block."""
        assignments = self._get_production_guard_assignments()
        assert "SECURE_HSTS_SECONDS" in assignments
        node = assignments["SECURE_HSTS_SECONDS"]
        assert isinstance(node, ast.Constant)
        assert node.value == 31536000

    def test_session_cookie_secure(self):
        """SESSION_COOKIE_SECURE = True in the 'if not DEBUG' block."""
        assignments = self._get_production_guard_assignments()
        assert "SESSION_COOKIE_SECURE" in assignments
        node = assignments["SESSION_COOKIE_SECURE"]
        assert isinstance(node, ast.Constant)
        assert node.value is True

    def test_csrf_cookie_secure(self):
        """CSRF_COOKIE_SECURE = True in the 'if not DEBUG' block."""
        assignments = self._get_production_guard_assignments()
        assert "CSRF_COOKIE_SECURE" in assignments
        node = assignments["CSRF_COOKIE_SECURE"]
        assert isinstance(node, ast.Constant)
        assert node.value is True

    def test_content_type_nosniff(self):
        """SECURE_CONTENT_TYPE_NOSNIFF = True in the 'if not DEBUG' block."""
        assignments = self._get_production_guard_assignments()
        assert "SECURE_CONTENT_TYPE_NOSNIFF" in assignments
        node = assignments["SECURE_CONTENT_TYPE_NOSNIFF"]
        assert isinstance(node, ast.Constant)
        assert node.value is True

    def test_ssl_redirect(self):
        """SECURE_SSL_REDIRECT = True in the 'if not DEBUG' block."""
        assignments = self._get_production_guard_assignments()
        assert "SECURE_SSL_REDIRECT" in assignments
        node = assignments["SECURE_SSL_REDIRECT"]
        assert isinstance(node, ast.Constant)
        assert node.value is True


# ============================================================================
# Note: Test routes (/yard-test-dev, /gate-test)
# ============================================================================
# These routes are gated behind `import.meta.env.DEV` in the Vue frontend
# router (frontend/src/router/index.ts). They only exist in development
# builds and are stripped from production bundles. No backend test needed.
