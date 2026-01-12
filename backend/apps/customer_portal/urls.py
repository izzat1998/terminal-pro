"""
URL routing for customer portal API endpoints.
"""

from rest_framework.routers import DefaultRouter

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

urlpatterns = router.urls
