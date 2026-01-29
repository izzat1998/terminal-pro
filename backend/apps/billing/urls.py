"""
URL configuration for billing app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdditionalChargeViewSet,
    BulkGenerateDraftsView,
    BulkStorageCostView,
    CustomerAdditionalChargeView,
    CustomerStorageCostView,
    ExpenseTypeViewSet,
    StorageCostView,
    TariffViewSet,
)


router = DefaultRouter()
router.register(r"tariffs", TariffViewSet, basename="tariff")
router.register(r"additional-charges", AdditionalChargeViewSet, basename="additional-charge")
router.register(r"expense-types", ExpenseTypeViewSet, basename="expense-type")

urlpatterns = [
    # Tariff management (admin)
    path("", include(router.urls)),
    # Storage cost calculation
    path(
        "container-entries/<int:entry_id>/storage-cost/",
        StorageCostView.as_view(),
        name="container-storage-cost",
    ),
    path(
        "storage-costs/calculate/",
        BulkStorageCostView.as_view(),
        name="bulk-storage-cost",
    ),
    path(
        "generate-all-drafts/",
        BulkGenerateDraftsView.as_view(),
        name="bulk-generate-drafts",
    ),
]

# Customer portal URLs (to be included in customer_portal app)
customer_urlpatterns = [
    path(
        "storage-costs/",
        CustomerStorageCostView.as_view(),
        name="customer-storage-costs",
    ),
    path(
        "additional-charges/",
        CustomerAdditionalChargeView.as_view(),
        name="customer-additional-charges",
    ),
]
