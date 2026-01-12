from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ContainerEntryViewSet,
    ContainerOwnerViewSet,
    CraneOperationViewSet,
    PlateRecognizerAPIView,
    PreOrderViewSet,
)


router = DefaultRouter()
router.register(r"entries", ContainerEntryViewSet)
router.register(r"owners", ContainerOwnerViewSet)
router.register(r"crane-operations", CraneOperationViewSet, basename="crane-operation")
router.register(r"plate-recognizer", PlateRecognizerAPIView, basename="plate-recognizer")
router.register(r"preorders", PreOrderViewSet, basename="preorder")

urlpatterns = [
    path("", include(router.urls)),
]
