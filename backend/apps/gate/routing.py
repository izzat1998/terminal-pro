from django.urls import re_path

from . import consumers


websocket_urlpatterns = [
    re_path(r"ws/gate/(?P<gate_id>\w+)/$", consumers.GateConsumer.as_asgi()),
]
