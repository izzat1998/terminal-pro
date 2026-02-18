from django.urls import path

from apps.gate.views import ANPRDetectionListView, ANPREventWebhookView, CameraPTZView

urlpatterns = [
    path("anpr-event/", ANPREventWebhookView.as_view(), name="anpr-event-webhook"),
    path("anpr-detections/", ANPRDetectionListView.as_view(), name="anpr-detections"),
    path("camera/ptz/", CameraPTZView.as_view(), name="camera-ptz"),
]
