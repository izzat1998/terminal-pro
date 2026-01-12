from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    CustomerLoginSerializer,
    ManagerSerializer,
    ManagerUpdateSerializer,
    RegisterSerializer,
    UnifiedLoginSerializer,
    UserSerializer,
)


class LoginView(APIView):
    """
    Unified authentication endpoint that handles both CustomUser and Manager.
    Accepts either:
    - username + password (CustomUser)
    - phone + password (Manager)
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Login",
        request=UnifiedLoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            400: OpenApiResponse(description="Invalid credentials"),
        },
        description="Authenticate user (username/password or phone/password) and return JWT tokens",
    )
    def post(self, request):
        serializer = UnifiedLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user_type = serializer.validated_data["user_type"]

        # Generate JWT with user_type claim
        refresh = RefreshToken.for_user(user)
        refresh["user_type"] = user_type

        if user_type == "manager":
            return Response(
                {
                    "success": True,
                    "user_type": user_type,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": ManagerSerializer(user).data,
                }
            )
        elif user_type == "customer":
            return Response(
                {
                    "success": True,
                    "user_type": user_type,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": CustomerLoginSerializer(user).data,
                }
            )
        else:
            return Response(
                {
                    "success": True,
                    "user_type": user_type,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                }
            )


class LogoutView(APIView):
    """
    User logout endpoint that blacklists the refresh token.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout",
        request=None,
        responses={
            200: OpenApiResponse(description="Logout successful"),
            400: OpenApiResponse(description="Invalid token"),
        },
        description="Logout user by blacklisting refresh token",
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"message": "Successfully logged out"}, status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    """
    User profile endpoint to get current user information.
    Returns appropriate serializer based on user type.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        responses={200: UserSerializer},
        description="Get current user profile (works for both API users and managers)",
    )
    def get(self, request):
        # Check user type
        if request.user.user_type == "manager":
            # It's a Manager
            serializer = ManagerSerializer(request.user)
        else:
            # It's an API user
            serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ManagerProfileView(APIView):
    """
    Manager self-profile endpoint.
    Allows managers to view and update their own profile.
    Only accessible to Manager users.
    """

    permission_classes = [IsAuthenticated]

    def _is_manager(self, user):
        """Check if user is a manager based on user_type."""
        return user.user_type == "manager"

    def _check_manager_permission(self, user):
        """Raise 403 if user is not a Manager."""
        if not self._is_manager(user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only managers can access this endpoint")

    @extend_schema(
        summary="Get manager profile",
        responses={200: ManagerSerializer},
        description="Get manager's own profile (managers only)",
    )
    def get(self, request):
        """Get current manager's profile."""
        self._check_manager_permission(request.user)
        serializer = ManagerSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Update manager profile",
        request=ManagerUpdateSerializer,
        responses={200: ManagerSerializer},
        description="Update manager's own profile (managers only)",
    )
    def patch(self, request):
        """Update current manager's profile (partial update)."""
        self._check_manager_permission(request.user)
        manager = request.user
        serializer = ManagerUpdateSerializer(manager, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_manager = serializer.save()
        return Response(ManagerSerializer(updated_manager).data)


class RegisterView(APIView):
    """
    User registration endpoint (admin only).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Register new user",
        request=RegisterSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Invalid data"),
            403: OpenApiResponse(description="Admin access required"),
        },
        description="Create new user account (admin only)",
    )
    def post(self, request):
        if not request.user.is_admin:
            return Response(
                {"error": "Only admin users can create new accounts"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
