"""JWT authentication middleware for Django Channels WebSockets."""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import CustomUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_str: str):
    """Validate JWT access token and return the user."""
    try:
        token = AccessToken(token_str)
        user_id = token["user_id"]
        return CustomUser.objects.get(id=user_id)
    except (InvalidToken, TokenError, CustomUser.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Extracts JWT token from WebSocket query string and attaches user to scope.

    Usage: ws://host/ws/gate/main/?token=<JWT_ACCESS_TOKEN>
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token_list = query_params.get("token", [])

        if token_list:
            scope["user"] = await get_user_from_token(token_list[0])
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
