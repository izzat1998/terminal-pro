"""
Centralized error response structure for consistent API error handling
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error response format
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # If DRF didn't handle it, handle our custom cases
    if response is None:
        return handle_non_drf_exceptions(exc, context)

    # Get the standard error response
    custom_response_data = get_error_response_format(
        error_code=get_error_code(exc),
        message=get_error_message(exc, response.data),
        details=format_error_details(response.data),
        status_code=response.status_code,
    )

    # Log the error
    log_error(exc, context, custom_response_data)

    response.data = custom_response_data
    return response


def handle_non_drf_exceptions(exc, context):
    """
    Handle exceptions that DRF doesn't handle by default
    """
    if isinstance(exc, BusinessLogicError):
        return Response(
            get_error_response_format(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
                status_code=status.HTTP_400_BAD_REQUEST,
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, DjangoValidationError):
        return Response(
            get_error_response_format(
                error_code="VALIDATION_ERROR",
                message="Ошибка валидации",
                details=format_django_validation_error(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, Http404):
        return Response(
            get_error_response_format(
                error_code="NOT_FOUND",
                message="Ресурс не найден",
                details=None,
                status_code=status.HTTP_404_NOT_FOUND,
            ),
            status=status.HTTP_404_NOT_FOUND,
        )

    # For unhandled exceptions, return a generic 500 error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return Response(
        get_error_response_format(
            error_code="INTERNAL_ERROR",
            message="Произошла внутренняя ошибка",
            details=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def get_error_response_format(error_code, message, details, status_code):
    """
    Standard error response format - Simplified Option 4
    """
    error_response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        },
        "timestamp": get_current_timestamp(),
    }

    if details:
        error_response["error"]["details"] = details

    return error_response


def get_error_code(exc):
    """
    Map exception types to custom error codes
    """
    error_code_map = {
        "ValidationError": "VALIDATION_ERROR",
        "PermissionDenied": "PERMISSION_DENIED",
        "NotAuthenticated": "AUTHENTICATION_REQUIRED",
        "AuthenticationFailed": "AUTHENTICATION_FAILED",
        "NotFound": "NOT_FOUND",
        "MethodNotAllowed": "METHOD_NOT_ALLOWED",
        "ParseError": "PARSE_ERROR",
        "UnsupportedMediaType": "UNSUPPORTED_MEDIA_TYPE",
        "Throttled": "RATE_LIMIT_EXCEEDED",
    }

    exception_name = exc.__class__.__name__
    return error_code_map.get(exception_name, "UNKNOWN_ERROR")


def get_error_message(exc, response_data):
    """
    Extract meaningful error message from exception.
    Creates descriptive messages that immediately tell users what's wrong.
    """
    if hasattr(exc, "detail"):
        if isinstance(exc.detail, str):
            return exc.detail
        elif isinstance(exc.detail, dict):
            # Build a descriptive message from field-specific errors
            return _build_validation_error_message(exc.detail)
        elif isinstance(exc.detail, list):
            # Return first error message
            return str(exc.detail[0]) if exc.detail else "Произошла ошибка"

    return str(exc)


def _build_validation_error_message(errors_dict):
    """
    Build a user-friendly validation error message from field errors.

    Examples:
    - Single field: "Номер контейнера: неверный формат ISO"
    - Multiple fields: "Ошибки: номер контейнера (неверный формат), статус (обязательное поле)"
    - Non-field errors: Returns the first non-field error directly
    """
    # Field name translations for common fields (Russian labels)
    field_labels = {
        "container_number": "номер контейнера",
        "container_iso_type": "тип контейнера",
        "status": "статус",
        "transport_type": "тип транспорта",
        "transport_number": "номер транспорта",
        "entry_time": "время въезда",
        "exit_date": "дата выезда",
        "cargo_weight": "вес груза",
        "cargo_name": "наименование груза",
        "client_name": "имя клиента",
        "destination": "направление",
        "location": "местоположение",
        "notes": "примечания",
        "username": "имя пользователя",
        "password": "пароль",
        "phone_number": "номер телефона",
        "email": "электронная почта",
        "first_name": "имя",
        "last_name": "фамилия",
        "company": "компания",
        "company_id": "компания",
        "plate_number": "номер машины",
        "operation_type": "тип операции",
        "license_plate": "госномер",
        "driver_name": "имя водителя",
        "container_owner": "владелец контейнера",
        "container_owner_id": "владелец контейнера",
        "name": "название",
        "login": "логин",
        "file": "файл",
        "image": "изображение",
        "photo": "фото",
    }

    # Handle non_field_errors specially - return them directly
    if "non_field_errors" in errors_dict:
        non_field = errors_dict["non_field_errors"]
        if isinstance(non_field, list) and non_field:
            return str(non_field[0])
        elif isinstance(non_field, str):
            return non_field

    # Filter out non_field_errors for field message building
    field_errors = {k: v for k, v in errors_dict.items() if k != "non_field_errors"}

    if not field_errors:
        return "Ошибка валидации"

    # Build descriptive messages for each field
    error_parts = []
    for field, errors in field_errors.items():
        # Get human-readable field label
        label = field_labels.get(field, field.replace("_", " "))

        # Get the first error message for this field
        if isinstance(errors, list) and errors:
            error_msg = str(errors[0])
        elif isinstance(errors, str):
            error_msg = errors
        else:
            error_msg = "некорректное значение"

        error_parts.append(f"{label}: {error_msg}")

    # Format based on number of errors
    if len(error_parts) == 1:
        return error_parts[0].capitalize()
    else:
        # Multiple errors - create a summary
        return "Ошибки валидации: " + "; ".join(error_parts)


def format_error_details(response_data):
    """
    Format error details consistently
    """
    if not response_data:
        return None

    if isinstance(response_data, dict):
        formatted_details = {}
        for field, errors in response_data.items():
            if isinstance(errors, list):
                formatted_details[field] = [str(error) for error in errors]
            else:
                formatted_details[field] = [str(errors)]
        return formatted_details

    if isinstance(response_data, list):
        return [str(error) for error in response_data]

    return [str(response_data)]


def format_django_validation_error(exc):
    """
    Format Django ValidationError for consistent response
    """
    if hasattr(exc, "message_dict"):
        # Field-specific errors
        formatted_details = {}
        for field, messages in exc.message_dict.items():
            formatted_details[field] = messages
        return formatted_details

    if hasattr(exc, "messages"):
        # Non-field errors
        return {"non_field_errors": exc.messages}

    return {"non_field_errors": [str(exc)]}


def log_error(exc, context, response_data):
    """
    Log error details for debugging
    """
    request = context.get("request")
    view = context.get("view")

    log_data = {
        "exception": exc.__class__.__name__,
        "message": str(exc),
        "path": request.path if request else None,
        "method": request.method if request else None,
        "view": view.__class__.__name__ if view else None,
        "user": str(request.user) if request and hasattr(request, "user") else None,
        "error_code": response_data["error"]["code"],
    }

    # Log as warning for client errors (4xx), error for server errors (5xx)
    status_code = (
        getattr(exc, "status_code", 500) if hasattr(exc, "status_code") else 500
    )
    if 400 <= status_code < 500:
        logger.warning(f"Client error: {log_data}")
    else:
        logger.error(f"Server error: {log_data}")


def get_current_timestamp():
    """
    Get current timestamp in ISO format
    """
    from django.utils import timezone

    return timezone.now().isoformat()


# Custom exception classes for business logic
class BusinessLogicError(Exception):
    """Base exception for business logic errors"""

    def __init__(self, message, error_code="BUSINESS_ERROR", details=None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class ContainerNotFoundError(BusinessLogicError):
    """Raised when container is not found"""

    def __init__(self, container_number):
        super().__init__(
            message=f"Контейнер {container_number} не найден",
            error_code="CONTAINER_NOT_FOUND",
            details={"container_number": container_number},
        )


class DuplicateEntryError(BusinessLogicError):
    """Raised when trying to create duplicate entry"""

    def __init__(self, container_number):
        super().__init__(
            message=f"Контейнер {container_number} уже имеет активную запись",
            error_code="DUPLICATE_ENTRY",
            details={"container_number": container_number},
        )


class InvalidContainerStateError(BusinessLogicError):
    """Raised when container is in invalid state for operation"""

    def __init__(self, container_number, current_state, required_state):
        super().__init__(
            message=f"Контейнер {container_number} находится в состоянии '{current_state}', но требуется '{required_state}'",
            error_code="INVALID_CONTAINER_STATE",
            details={
                "container_number": container_number,
                "current_state": current_state,
                "required_state": required_state,
            },
        )
