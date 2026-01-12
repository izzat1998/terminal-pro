from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .company_views import CompanyViewSet
from .customer_views import CustomerViewSet
from .manager_views import GateAccessCheckView, ManagerViewSet


# Create router for viewsets
router = DefaultRouter()
router.register(r"managers", ManagerViewSet, basename="manager")
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"companies", CompanyViewSet, basename="company")

urlpatterns = [
    # Auth endpoints
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path(
        "manager/profile/", views.ManagerProfileView.as_view(), name="manager-profile"
    ),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # Gate access check (public endpoint for gate terminals)
    path(
        "managers/gate-access/", GateAccessCheckView.as_view(), name="gate-access-check"
    ),
    # Manager and Customer endpoints (admin only)
    path("", include(router.urls)),
]
