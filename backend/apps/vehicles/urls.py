from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DestinationViewSet,
    PlateRecognizerAPIView,
    VehicleChoicesAPIView,
    VehicleEntryViewSet,
    VehicleStatisticsAPIView,
)


router = DefaultRouter()
router.register(r"destinations", DestinationViewSet, basename="destination")
router.register(r"entries", VehicleEntryViewSet, basename="vehicleentry")

urlpatterns = [
    path("", include(router.urls)),
    path("plate-recognize/", PlateRecognizerAPIView.as_view(), name="plate-recognize"),
    path("choices/", VehicleChoicesAPIView.as_view(), name="vehicle-choices"),
    path("statistics/", VehicleStatisticsAPIView.as_view(), name="vehicle-statistics"),
]
