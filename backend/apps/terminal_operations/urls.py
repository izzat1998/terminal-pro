from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ContainerEntryViewSet,
    ContainerOwnerViewSet,
    CraneOperationViewSet,
    PlacementViewSet,
    PlateRecognizerAPIView,
    PreOrderViewSet,
    TerminalVehicleViewSet,
    WorkOrderViewSet,
)


router = DefaultRouter()
router.register(r"entries", ContainerEntryViewSet)
router.register(r"owners", ContainerOwnerViewSet)
router.register(r"crane-operations", CraneOperationViewSet, basename="crane-operation")
router.register(
    r"plate-recognizer", PlateRecognizerAPIView, basename="plate-recognizer"
)
router.register(r"preorders", PreOrderViewSet, basename="preorder")
router.register(r"placement", PlacementViewSet, basename="placement")
router.register(r"work-orders", WorkOrderViewSet, basename="work-order")
router.register(r"terminal-vehicles", TerminalVehicleViewSet, basename="terminal-vehicle")

urlpatterns = [
    path("", include(router.urls)),
]
