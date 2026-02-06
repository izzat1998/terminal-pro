"""
Unit tests verifying standard response format on all fixed endpoints.

Tests view methods directly with mocked dependencies - no database access.
Every API endpoint should return responses in the standard format:
- Success: {"success": True, "data": ..., "message": ...}
- Error:   {"success": False, "error": {"code": ..., "message": ...}, ...}
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory


factory = APIRequestFactory()


# ============================================================================
# Helper Functions
# ============================================================================

def assert_success_response(response_data):
    """Validate that a response follows the standard success format."""
    assert "success" in response_data, f"Missing 'success' key in response: {response_data}"
    assert response_data["success"] is True, f"Expected success=True, got {response_data['success']}"


def assert_error_response(response_data):
    """Validate that a response follows the standard error format."""
    assert "success" in response_data, f"Missing 'success' key in response: {response_data}"
    assert response_data["success"] is False, f"Expected success=False, got {response_data['success']}"
    assert "error" in response_data, f"Missing 'error' key in response: {response_data}"
    assert isinstance(response_data["error"], dict), f"'error' should be dict, got {type(response_data['error'])}"
    assert "code" in response_data["error"], f"Missing 'code' in error: {response_data['error']}"
    assert "message" in response_data["error"], f"Missing 'message' in error: {response_data['error']}"


def _make_drf_request(method="get", path="/", data=None, user=None):
    """Create a DRF Request object (has .data attribute) with a mock user."""
    from django.utils.datastructures import MultiValueDict

    if method == "post":
        wsgi_request = factory.post(path, data or {}, format="json")
    elif method == "delete":
        wsgi_request = factory.delete(path)
    else:
        wsgi_request = factory.get(path)

    # Wrap in DRF Request so .data works
    drf_request = Request(wsgi_request)

    # For POST/DELETE, pre-set _data to avoid re-parsing from the WSGI stream
    # which can fail without proper parsers in unit test context
    if method in ("post", "delete"):
        drf_request._data = data or {}
        drf_request._files = MultiValueDict()
        drf_request._full_data = data or {}

    if user is not None:
        drf_request._user = user
        wsgi_request.user = user
    else:
        drf_request._user = _make_mock_user()
        wsgi_request.user = drf_request._user

    return drf_request


def _make_mock_user(is_admin=False, is_authenticated=True, user_type="admin", username="testuser"):
    """Create a mock user object."""
    user = MagicMock()
    user.is_admin = is_admin
    user.is_authenticated = is_authenticated
    user.is_staff = is_admin
    user.is_active = True
    user.user_type = user_type
    user.username = username
    user.email = "test@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.id = 1
    user.pk = 1
    return user


# ============================================================================
# Auth Endpoint Tests - LogoutView
# ============================================================================

@pytest.mark.unit
class TestLogoutResponseFormat:
    """POST /api/auth/logout/ returns standard format."""

    def test_logout_success_format(self):
        """Successful logout returns {success: True, message: ...}."""
        from apps.accounts.views import LogoutView

        request = _make_drf_request("post", "/api/auth/logout/", {"refresh": "valid-token"})
        view = LogoutView()

        with patch("apps.accounts.views.RefreshToken") as mock_token_cls:
            mock_token = MagicMock()
            mock_token_cls.return_value = mock_token
            response = view.post(request)

        assert response.status_code == status.HTTP_200_OK
        assert_success_response(response.data)
        assert "message" in response.data

    def test_logout_invalid_token_error_format(self):
        """Logout with invalid token returns standard error format."""
        from apps.accounts.views import LogoutView
        from rest_framework_simplejwt.exceptions import TokenError

        request = _make_drf_request("post", "/api/auth/logout/", {"refresh": "invalid-token"})
        view = LogoutView()

        with patch("apps.accounts.views.RefreshToken") as mock_token_cls:
            mock_token_cls.side_effect = TokenError("Token is invalid")
            response = view.post(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert_error_response(response.data)
        assert response.data["error"]["code"] == "INVALID_TOKEN"


# ============================================================================
# Auth Endpoint Tests - RegisterView
# ============================================================================

@pytest.mark.unit
class TestRegisterResponseFormat:
    """POST /api/auth/register/ returns standard format."""

    def test_register_success_format(self):
        """Successful registration returns {success: True, data: ...}."""
        from apps.accounts.views import RegisterView

        admin_user = _make_mock_user(is_admin=True)
        request = _make_drf_request("post", "/api/auth/register/", {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
        }, user=admin_user)

        view = RegisterView()

        mock_created_user = _make_mock_user(username="newuser")
        mock_created_user.profile_company = None

        with patch("apps.accounts.views.RegisterSerializer") as mock_ser_cls, \
             patch("apps.accounts.views.UserSerializer") as mock_user_ser_cls:
            mock_ser = MagicMock()
            mock_ser.is_valid.return_value = True
            mock_ser.save.return_value = mock_created_user
            mock_ser_cls.return_value = mock_ser

            mock_user_ser = MagicMock()
            mock_user_ser.data = {"id": 1, "username": "newuser", "email": "new@example.com"}
            mock_user_ser_cls.return_value = mock_user_ser

            response = view.post(request)

        assert response.status_code == status.HTTP_201_CREATED
        assert_success_response(response.data)
        assert "data" in response.data

    def test_register_validation_error_format(self):
        """Registration validation errors return standard error format."""
        from apps.accounts.views import RegisterView

        admin_user = _make_mock_user(is_admin=True)
        request = _make_drf_request("post", "/api/auth/register/", {
            "username": "newuser",
            "password": "newpass123",
            "password_confirm": "differentpass",
        }, user=admin_user)

        view = RegisterView()

        with patch("apps.accounts.views.RegisterSerializer") as mock_ser_cls:
            mock_ser = MagicMock()
            mock_ser.is_valid.return_value = False
            mock_ser.errors = {"non_field_errors": ["Пароли не совпадают"]}
            mock_ser_cls.return_value = mock_ser

            response = view.post(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert_error_response(response.data)
        assert response.data["error"]["code"] == "VALIDATION_ERROR"

    def test_register_non_admin_forbidden_format(self):
        """Non-admin registration attempt returns standard error format."""
        from apps.accounts.views import RegisterView

        regular_user = _make_mock_user(is_admin=False)
        request = _make_drf_request("post", "/api/auth/register/", {}, user=regular_user)

        view = RegisterView()
        response = view.post(request)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert_error_response(response.data)
        assert response.data["error"]["code"] == "FORBIDDEN"


# ============================================================================
# Auth Endpoint Tests - ProfileView
# ============================================================================

@pytest.mark.unit
class TestProfileResponseFormat:
    """GET /api/auth/profile/ returns standard format."""

    def test_profile_success_format(self):
        """Profile endpoint returns {success: True, data: ...}."""
        from apps.accounts.views import ProfileView

        mock_user = _make_mock_user(username="profuser")
        mock_user.user_type = "admin"
        request = _make_drf_request("get", "/api/auth/profile/", user=mock_user)

        view = ProfileView()

        with patch("apps.accounts.views.UserSerializer") as mock_ser_cls:
            mock_ser = MagicMock()
            mock_ser.data = {"id": 1, "username": "profuser", "email": "test@example.com"}
            mock_ser_cls.return_value = mock_ser

            response = view.get(request)

        assert response.status_code == status.HTTP_200_OK
        assert_success_response(response.data)
        assert "data" in response.data


# ============================================================================
# Customer Portal Tests - Statistics
# ============================================================================

@pytest.mark.unit
class TestCustomerStatisticsResponseFormat:
    """GET /api/customer/profile/statistics/ returns standard format."""

    def test_statistics_no_company_error_format(self):
        """Statistics with no company returns standard error format."""
        from apps.customer_portal.views import CustomerProfileViewSet

        # Create a user spec that does NOT have customer_profile or company attrs
        mock_user = MagicMock(spec=["is_authenticated", "is_active", "user_type", "username", "id", "pk"])
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.user_type = "customer"
        mock_user.username = "testcustomer"
        mock_user.id = 1
        mock_user.pk = 1
        request = _make_drf_request("get", "/api/customer/profile/statistics/", user=mock_user)

        view = CustomerProfileViewSet()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {}

        response = view.statistics(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert_error_response(response.data)
        assert response.data["error"]["code"] == "COMPANY_NOT_FOUND"


# ============================================================================
# Customer Portal Tests - PreOrder
# ============================================================================

@pytest.mark.unit
class TestCustomerPreOrderResponseFormat:
    """Customer preorder endpoints return standard format."""

    def test_create_preorder_service_error_format(self):
        """Creating preorder that fails in service returns standard error format."""
        from apps.customer_portal.views import CustomerPreOrderViewSet
        from apps.core.exceptions import BusinessLogicError

        mock_user = _make_mock_user(user_type="customer")
        request = _make_drf_request("post", "/api/customer/preorders/", {
            "plate_number": "01A123BC",
            "operation_type": "LOAD",
        }, user=mock_user)

        view = CustomerPreOrderViewSet()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {}

        with patch("apps.customer_portal.views.CustomerPreOrderCreateSerializer") as mock_ser_cls:
            mock_ser = MagicMock()
            mock_ser.is_valid.return_value = True
            mock_ser.validated_data = {
                "plate_number": "01A123BC",
                "operation_type": "LOAD",
            }
            mock_ser_cls.return_value = mock_ser

            with patch("apps.customer_portal.views.PreOrderService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.create_preorder.side_effect = BusinessLogicError(
                    "Ошибка создания заявки", error_code="ERROR"
                )
                mock_svc_cls.return_value = mock_svc

                response = view.create(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert_error_response(response.data)

    def test_cancel_non_pending_preorder_error_format(self):
        """Cancelling a non-PENDING preorder returns standard error format."""
        from apps.customer_portal.views import CustomerPreOrderViewSet
        from apps.core.exceptions import BusinessLogicError

        mock_user = _make_mock_user(user_type="customer")
        request = _make_drf_request("delete", "/api/customer/preorders/1/", user=mock_user)

        mock_preorder = MagicMock()
        mock_preorder.id = 1
        mock_preorder.status = "MATCHED"
        mock_preorder.customer = mock_user

        view = CustomerPreOrderViewSet()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {"pk": "1"}

        with patch.object(view, "get_object", return_value=mock_preorder):
            with patch("apps.customer_portal.views.PreOrderService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc.cancel_order.side_effect = BusinessLogicError(
                    "Можно отменить только активные заявки",
                    error_code="ORDER_NOT_PENDING",
                )
                mock_svc_cls.return_value = mock_svc

                response = view.destroy(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert_error_response(response.data)


# ============================================================================
# Vehicle Endpoint Tests - check_plate
# ============================================================================

@pytest.mark.unit
class TestVehicleCheckPlateResponseFormat:
    """GET /api/vehicles/entries/check-plate/ returns standard format."""

    def test_check_plate_empty_returns_success_format(self):
        """Check plate with empty plate returns {success: True, data: ...}."""
        from apps.vehicles.views import VehicleEntryViewSet

        request = _make_drf_request("get", "/api/vehicles/entries/check-plate/")

        view = VehicleEntryViewSet()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {}

        response = view.check_plate(request)

        assert response.status_code == status.HTTP_200_OK
        assert_success_response(response.data)
        assert "data" in response.data
        assert response.data["data"]["on_terminal"] is False

    def test_check_plate_not_found_returns_success_format(self):
        """Check plate for non-existent plate returns {success: True, data: {on_terminal: False}}."""
        from apps.vehicles.views import VehicleEntryViewSet

        request = _make_drf_request("get", "/api/vehicles/entries/check-plate/?license_plate=ZZZZZZZ")

        view = VehicleEntryViewSet()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {}

        mock_qs = MagicMock()
        mock_qs.first.return_value = None

        with patch("apps.vehicles.views.VehicleEntry") as mock_model:
            mock_model.objects.filter.return_value = mock_qs
            response = view.check_plate(request)

        assert response.status_code == status.HTTP_200_OK
        assert_success_response(response.data)
        assert response.data["data"]["on_terminal"] is False

    def test_check_plate_found_returns_success_format(self):
        """Check plate for on-terminal vehicle returns {success: True, data: {on_terminal: True, entry: ...}}."""
        from apps.vehicles.views import VehicleEntryViewSet
        from django.utils import timezone

        request = _make_drf_request("get", "/api/vehicles/entries/check-plate/?license_plate=01X999YY")

        view = VehicleEntryViewSet()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {}

        mock_entry = MagicMock()
        mock_entry.id = 42
        mock_entry.license_plate = "01X999YY"
        mock_entry.entry_time = timezone.now()
        mock_entry.vehicle_type = "CARGO"

        mock_qs = MagicMock()
        mock_qs.first.return_value = mock_entry

        with patch("apps.vehicles.views.VehicleEntry") as mock_model:
            mock_model.objects.filter.return_value = mock_qs
            response = view.check_plate(request)

        assert response.status_code == status.HTTP_200_OK
        assert_success_response(response.data)
        assert response.data["data"]["on_terminal"] is True
        assert "entry" in response.data["data"]
        assert response.data["data"]["entry"]["id"] == 42


# ============================================================================
# Vehicle Endpoint Tests - PlateRecognizerAPIView
# ============================================================================

@pytest.mark.unit
class TestPlateRecognizerResponseFormat:
    """POST /api/vehicles/plate-recognize/ returns standard format."""

    def test_plate_recognizer_validation_error_format(self):
        """Plate recognizer without image returns standard error format."""
        from apps.vehicles.views import PlateRecognizerAPIView

        request = _make_drf_request("post", "/api/vehicles/plate-recognize/", {})
        view = PlateRecognizerAPIView()

        with patch("apps.vehicles.views.PlateRecognitionRequestSerializer") as mock_ser_cls:
            mock_ser = MagicMock()
            mock_ser.is_valid.return_value = False
            mock_ser.errors = {"image": ["Обязательное поле."]}
            mock_ser_cls.return_value = mock_ser

            response = view.post(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert_error_response(response.data)
        assert response.data["error"]["code"] == "VALIDATION_ERROR"


# ============================================================================
# Language Compliance Tests
# ============================================================================

@pytest.mark.unit
class TestErrorMessagesInRussian:
    """Error messages from fixed endpoints should be in Russian."""

    def test_logout_error_message_is_russian(self):
        """Logout error message uses Russian text."""
        from apps.accounts.views import LogoutView
        from rest_framework_simplejwt.exceptions import TokenError

        request = _make_drf_request("post", "/api/auth/logout/", {"refresh": "invalid"})
        view = LogoutView()

        with patch("apps.accounts.views.RefreshToken") as mock_token_cls:
            mock_token_cls.side_effect = TokenError("Token is invalid")
            response = view.post(request)

        message = response.data["error"]["message"]
        assert any(
            word in message for word in ["Недействительный", "токен"]
        ), f"Error message should be in Russian, got: {message}"

    def test_register_forbidden_message_is_russian(self):
        """Register non-admin error message uses Russian text."""
        from apps.accounts.views import RegisterView

        regular_user = _make_mock_user(is_admin=False)
        request = _make_drf_request("post", "/api/auth/register/", {}, user=regular_user)

        view = RegisterView()
        response = view.post(request)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        message = response.data["error"]["message"]
        assert any(
            word in message for word in ["администратор", "Только", "учётн"]
        ), f"Error message should be in Russian, got: {message}"

    def test_customer_statistics_error_message_is_russian(self):
        """Customer statistics error message uses Russian text."""
        from apps.customer_portal.views import CustomerProfileViewSet

        mock_user = MagicMock(spec=["is_authenticated", "is_active", "user_type", "username", "id", "pk"])
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.user_type = "customer"
        mock_user.id = 1
        mock_user.pk = 1
        request = _make_drf_request("get", "/api/customer/profile/statistics/", user=mock_user)

        view = CustomerProfileViewSet()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {}

        response = view.statistics(request)

        message = response.data["error"]["message"]
        assert any(
            word in message for word in ["Компания", "найден", "компания"]
        ), f"Error message should be in Russian, got: {message}"

    def test_files_missing_category_error_is_russian(self):
        """Files by_category missing parameter returns Russian error message."""
        from apps.files.views import FileViewSet

        request = _make_drf_request("get", "/api/files/files/by-category/")

        view = FileViewSet()
        view.request = request
        view.format_kwarg = None
        view.kwargs = {}

        response = view.by_category(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert_error_response(response.data)
        message = response.data["error"]["message"]
        assert any(
            word in message for word in ["Параметр", "обязателен", "category"]
        ), f"Error message should be in Russian, got: {message}"
