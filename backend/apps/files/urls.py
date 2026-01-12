from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FileAttachmentViewSet, FileCategoryViewSet, FileViewSet


router = DefaultRouter()
router.register(r"files", FileViewSet)
router.register(r"categories", FileCategoryViewSet)
router.register(r"attachments", FileAttachmentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
