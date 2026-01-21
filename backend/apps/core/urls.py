from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TelegramActivityLogViewSet, TestTelegramGroupView


router = DefaultRouter()
router.register(r"activity-logs", TelegramActivityLogViewSet, basename="activity-log")

urlpatterns = [
    path("", include(router.urls)),
    path("test-group/", TestTelegramGroupView.as_view(), name="test-telegram-group"),
]
