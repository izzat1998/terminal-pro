"""
URL configuration for terminal_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import AllowAny


# In development, make Swagger UI publicly accessible (no login required)
schema_permission_classes = [AllowAny] if settings.DEBUG else None

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/terminal/", include("apps.terminal_operations.urls")),
    path("api/files/", include("apps.files.urls")),
    path("api/vehicles/", include("apps.vehicles.urls")),
    path("api/customer/", include("apps.customer_portal.urls")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/telegram/", include("apps.core.urls")),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=schema_permission_classes),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema", permission_classes=schema_permission_classes
        ),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema", permission_classes=schema_permission_classes
        ),
        name="redoc",
    ),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
