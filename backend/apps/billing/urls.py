"""
URL configuration for billing app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdditionalChargeViewSet,
    BulkGenerateDraftsView,
    BulkStorageCostView,
    CompanyStatementExportActHtmlPreviewView,
    CompanyStatementExportActPreviewView,
    CompanyStatementExportActView,
    CompanyStatementExportHtmlPreviewView,
    ContainerBillingDetailView,
    CustomerAdditionalChargeView,
    CustomerStorageCostView,
    ExchangeRateView,
    ExpenseTypeViewSet,
    StorageCostView,
    TariffViewSet,
    TerminalSettingsView,
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
    path(
        "terminal-settings/",
        TerminalSettingsView.as_view(),
        name="terminal-settings",
    ),
    # Exchange rate from CBU
    path(
        "exchange-rate/",
        ExchangeRateView.as_view(),
        name="exchange-rate",
    ),
    # Счёт-фактура export (admin, per company)
    path(
        "companies/<slug:slug>/statements/<int:year>/<int:month>/export/act/",
        CompanyStatementExportActView.as_view(),
        name="company-statement-export-act",
    ),
    path(
        "companies/<slug:slug>/statements/<int:year>/<int:month>/export/act-preview/",
        CompanyStatementExportActPreviewView.as_view(),
        name="company-statement-export-act-preview",
    ),
    path(
        "companies/<slug:slug>/statements/<int:year>/<int:month>/export/html-preview/",
        CompanyStatementExportHtmlPreviewView.as_view(),
        name="company-statement-export-html-preview",
    ),
    path(
        "companies/<slug:slug>/statements/<int:year>/<int:month>/export/act-html-preview/",
        CompanyStatementExportActHtmlPreviewView.as_view(),
        name="company-statement-export-act-html-preview",
    ),
    # Container billing detail (admin)
    path(
        "container-entry/<int:entry_id>/billing-detail/",
        ContainerBillingDetailView.as_view(),
        name="container-billing-detail",
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
