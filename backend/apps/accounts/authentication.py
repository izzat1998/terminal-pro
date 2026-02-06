"""
Custom JWT authentication for unified CustomUser model.
"""

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .models import CustomUser


class DevAutoAuthentication(BaseAuthentication):
    """
    ⚠️  WARNING: Development-only authentication that auto-logs in as admin.
    Only active when DEBUG=True. Returns None if admin not found (falls through to next auth).

    SECURITY: This class MUST NEVER be active in production.
    It is conditionally included in REST_FRAMEWORK settings only when DEV_AUTO_AUTH=True
    AND DEBUG=True. If you see this class active in production logs, it is a critical
    security incident — disable DEV_AUTO_AUTH immediately.
    """

    def authenticate(self, request):
        if not settings.DEBUG:
            return None

        # Skip if already authenticated or has Authorization header (let JWT handle it)
        if request.META.get("HTTP_AUTHORIZATION"):
            return None

        try:
            admin_user = CustomUser.objects.filter(
                user_type="admin", is_active=True
            ).first()
            if admin_user:
                return (admin_user, None)
        except Exception:
            pass

        return None


class UnifiedJWTAuthentication(JWTAuthentication):
    """
    JWT authentication for unified CustomUser model.
    All users (both API and managers) are stored in CustomUser with user_type field.
    """

    def get_user(self, validated_token):
        """
        Get user from CustomUser model by ID.
        """
        user_id = validated_token.get("user_id")

        if not user_id:
            raise AuthenticationFailed("Token is missing user_id")

        try:
            return CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            raise AuthenticationFailed("User not found")
