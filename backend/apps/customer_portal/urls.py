"""
URL routing for customer portal API endpoints.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.billing.views import (
    CustomerAdditionalChargeView,
    CustomerAvailablePeriodsView,
    CustomerBulkStorageCostView,
    CustomerContainerBillingDetailView,
    CustomerStatementExportActHtmlPreviewView,
    CustomerStatementExportActPreviewView,
    CustomerStatementExportActView,
    CustomerStatementExportExcelView,
    CustomerStatementExportHtmlPreviewView,
    CustomerStatementExportPdfView,
    CustomerStatementListView,
    CustomerStatementView,
    CustomerStorageCostExportView,
    CustomerStorageCostView,
)

from .views import (
    CustomerContainerEntryViewSet,
    CustomerPreOrderViewSet,
    CustomerProfileViewSet,
)


# Create router and register viewsets
router = DefaultRouter()

# Profile endpoints: /api/customer/profile/
router.register(r"profile", CustomerProfileViewSet, basename="customer-profile")

# Container endpoints: /api/customer/containers/
router.register(
    r"containers", CustomerContainerEntryViewSet, basename="customer-containers"
)

# Pre-order endpoints: /api/customer/preorders/
router.register(r"preorders", CustomerPreOrderViewSet, basename="customer-preorders")

urlpatterns = router.urls + [
    # Storage costs export: /api/customer/storage-costs/export/
    path(
        "storage-costs/export/",
        CustomerStorageCostExportView.as_view(),
        name="customer-storage-costs-export",
    ),
    # Storage costs endpoint: /api/customer/storage-costs/
    path(
        "storage-costs/",
        CustomerStorageCostView.as_view(),
        name="customer-storage-costs",
    ),
    # Bulk storage cost calculation for customer
    path(
        "storage-costs/calculate/",
        CustomerBulkStorageCostView.as_view(),
        name="customer-storage-costs-calculate",
    ),
    # Monthly billing statements
    path(
        "billing/statements/",
        CustomerStatementListView.as_view(),
        name="customer-statement-list",
    ),
    path(
        "billing/statements/<int:year>/<int:month>/",
        CustomerStatementView.as_view(),
        name="customer-statement-detail",
    ),
    path(
        "billing/available-periods/",
        CustomerAvailablePeriodsView.as_view(),
        name="customer-available-periods",
    ),
    # Statement export endpoints
    path(
        "billing/statements/<int:year>/<int:month>/export/excel/",
        CustomerStatementExportExcelView.as_view(),
        name="customer-statement-export-excel",
    ),
    path(
        "billing/statements/<int:year>/<int:month>/export/pdf/",
        CustomerStatementExportPdfView.as_view(),
        name="customer-statement-export-pdf",
    ),
    path(
        "billing/statements/<int:year>/<int:month>/export/act/",
        CustomerStatementExportActView.as_view(),
        name="customer-statement-export-act",
    ),
    path(
        "billing/statements/<int:year>/<int:month>/export/act-preview/",
        CustomerStatementExportActPreviewView.as_view(),
        name="customer-statement-export-act-preview",
    ),
    path(
        "billing/statements/<int:year>/<int:month>/export/html-preview/",
        CustomerStatementExportHtmlPreviewView.as_view(),
        name="customer-statement-export-html-preview",
    ),
    path(
        "billing/statements/<int:year>/<int:month>/export/act-html-preview/",
        CustomerStatementExportActHtmlPreviewView.as_view(),
        name="customer-statement-export-act-html-preview",
    ),
    # Additional charges endpoint: /api/customer/additional-charges/
    path(
        "additional-charges/",
        CustomerAdditionalChargeView.as_view(),
        name="customer-additional-charges",
    ),
    # Container billing detail (customer)
    path(
        "container-entry/<int:entry_id>/billing-detail/",
        CustomerContainerBillingDetailView.as_view(),
        name="customer-container-billing-detail",
    ),
]
