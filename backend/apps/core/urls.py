from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TelegramActivityLogViewSet


router = DefaultRouter()
router.register(r"activity-logs", TelegramActivityLogViewSet, basename="activity-log")

urlpatterns = [
    path("", include(router.urls)),
]
