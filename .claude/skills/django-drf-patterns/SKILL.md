---
name: django-drf-patterns
description: Use when writing or modifying Django backend code - covers service layer, custom exceptions, serializers, views, permissions, and testing patterns specific to this MTT codebase
---

# MTT Django + DRF Patterns

Quick reference for the actual patterns used in `backend/`.

## Service Layer

All business logic in `apps/*/services/`, inheriting from `BaseService`:

```python
from django.db import transaction
from apps.core.services import BaseService
from apps.core.exceptions import BusinessLogicError

class ContainerEntryService(BaseService):
    def __init__(self):
        super().__init__()  # Sets up self.logger
        self._event_service = None

    @property
    def event_service(self):
        """Lazy load to avoid circular imports"""
        if self._event_service is None:
            self._event_service = ContainerEventService()
        return self._event_service

    @transaction.atomic
    def create_entry(self, container_number, status, user, **kwargs):
        # 1. Validate
        if not container_number:
            raise BusinessLogicError("Номер контейнера обязателен", error_code="MISSING_CONTAINER")

        # 2. Get/create related objects
        container, _ = Container.objects.get_or_create(
            container_number=container_number.upper(),
            defaults={"iso_type": kwargs.get("iso_type", "22G1")},
        )

        # 3. Check business rules
        if self._has_recent_entry(container):
            raise DuplicateEntryError(container_number)

        # 4. Create
        entry = ContainerEntry.objects.create(container=container, status=status, recorded_by=user)

        # 5. Events + logging
        self.event_service.create_entry_created_event(container_entry=entry, performed_by=user, source="API")
        self.logger.info(f"Created entry for container {container_number}")
        return entry
```

**Rules:**
- `@transaction.atomic` on any method that writes multiple objects
- Raise custom exceptions (Russian messages) for business rules
- Lazy `@property` for cross-service dependencies
- `self.logger.info()` for actions, `self.logger.error()` for failures

## Custom Exceptions

Located in `apps/core/exceptions.py`. Auto-handled by `custom_exception_handler`.

```python
from apps.core.exceptions import BusinessLogicError, ContainerNotFoundError, DuplicateEntryError, InvalidContainerStateError

# Base - use for generic business errors
raise BusinessLogicError("Сообщение об ошибке", error_code="ERROR_CODE", details={...})

# Specific subclasses
raise ContainerNotFoundError(container_number)       # code="CONTAINER_NOT_FOUND"
raise DuplicateEntryError(container_number)           # code="DUPLICATE_ENTRY"
raise InvalidContainerStateError(number, current, required)  # code="INVALID_CONTAINER_STATE"
```

**Auto-formatted response:**
```json
{"success": false, "error": {"code": "ERROR_CODE", "message": "..."}, "timestamp": "..."}
```

## View Patterns

### ViewSet (CRUD endpoints)

```python
class CraneOperationViewSet(viewsets.ModelViewSet):
    queryset = CraneOperation.objects.all()
    serializer_class = CraneOperationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CraneOperationFilter
    search_fields = ["container__container_number"]
    ordering_fields = ["operation_date"]
    ordering = ["-operation_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = CraneOperationService()

    def perform_create(self, serializer):
        operation = self.service.create_operation(
            entry_id=serializer.validated_data["entry_id"],
            operation_date=serializer.validated_data["operation_date"],
        )
        serializer.instance = operation

    @extend_schema(summary="Create for entry")
    @action(detail=False, methods=["post"], url_path="for-entry")
    def for_entry(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self.service.create_operation(...)
        return Response({"success": True, "data": CraneOperationSerializer(result).data}, status=status.HTTP_201_CREATED)
```

### APIView (non-CRUD endpoints)

```python
class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Login", request=UnifiedLoginSerializer)
    def post(self, request):
        serializer = UnifiedLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response({"success": True, "access": str(refresh.access_token), "refresh": str(refresh), "user": ManagerSerializer(user).data})
```

**Response format - always:**
```python
# Success
Response({"success": True, "data": serializer.data, "message": "Optional Russian message"})

# Error (auto via exception handler, or manual):
Response({"success": False, "error": {"code": "CODE", "message": "Russian message"}}, status=status.HTTP_400_BAD_REQUEST)
```

## Serializer Patterns

```python
class ContainerEntrySerializer(serializers.ModelSerializer):
    # Write-only inputs
    container_number = serializers.CharField(write_only=True, required=True)
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(is_active=True), source="company", write_only=True, required=False, allow_null=True
    )

    # Read-only computed
    dwell_time_days = serializers.SerializerMethodField()

    # Nested read-only
    crane_operations = CraneOperationSerializer(many=True, read_only=True)

    # Write-only nested
    crane_operations_data = CraneOperationWriteSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = ContainerEntry
        fields = [...]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"slug": {"required": False}}

    def validate_name(self, value):
        if self.instance and Model.objects.filter(name=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("Уже существует")
        return value

    def get_dwell_time_days(self, obj):
        if obj.exit_date:
            return (obj.exit_date - obj.entry_time).days
        return None
```

## Permissions

```python
from rest_framework.permissions import IsAuthenticated, AllowAny

# Custom permissions in apps/customer_portal/permissions.py:
from apps.customer_portal.permissions import IsCustomer, IsCustomerOwner, HasCompanyAccess

# Usage:
permission_classes = [IsAuthenticated]              # Standard endpoints
permission_classes = [AllowAny]                      # Login/register
permission_classes = [IsCustomer, HasCompanyAccess]  # Customer portal
```

## URL Routing

```python
router = DefaultRouter()
router.register(r"managers", ManagerViewSet, basename="manager")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("", include(router.urls)),
]
```

## Filtering

```python
from django_filters import FilterSet, DateTimeFilter

class ContainerEntryFilter(FilterSet):
    entry_date_after = DateTimeFilter(field_name='entry_time', lookup_expr='gte')
    entry_date_before = DateTimeFilter(field_name='entry_time', lookup_expr='lte')

    class Meta:
        model = ContainerEntry
        fields = ['status', 'transport_type', 'container_owner']
```

## Models

```python
from apps.core.models import TimestampedModel  # Provides created_at, updated_at

class ContainerEntry(TimestampedModel):
    container = models.ForeignKey(Container, on_delete=models.PROTECT, related_name="entries")
    status = models.CharField(max_length=20, choices=[("LADEN", "Laden"), ("EMPTY", "Empty")], db_index=True)
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-entry_time"]
        indexes = [models.Index(fields=["status", "-entry_time"])]
```

**FK conventions:** `PROTECT` for critical, `SET_NULL` for optional, `CASCADE` for dependent.

## Testing

```python
# tests/conftest.py fixtures:
@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client_with_token(admin_user):
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client, admin_user

@pytest.fixture
def container_factory(db):
    def _create(**kwargs):
        return Container.objects.create(container_number=kwargs.get('number', 'TEST1234567'), ...)
    return _create
```

```bash
pytest                     # All tests
pytest --cov=apps          # With coverage
pytest tests/containers/   # Specific app
```

## Utilities

```python
from apps.core.utils import safe_int_param

# Safe query param parsing (instead of bare int())
entry_id = safe_int_param(request.query_params.get("entry_id"), default=None, min_val=1)
```

## Quick Checklist

- [ ] Business logic in service, not view
- [ ] `@transaction.atomic` on multi-write methods
- [ ] Custom exceptions with Russian messages
- [ ] Response: `{"success": bool, "data"?: ..., "error"?: ...}`
- [ ] `read_only_fields` includes `id`, `created_at`, `updated_at`
- [ ] `@extend_schema()` on endpoints
- [ ] `safe_int_param()` instead of bare `int()`
