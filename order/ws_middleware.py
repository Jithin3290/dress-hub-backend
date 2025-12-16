from django.conf import settings
from channels.db import database_sync_to_async
import jwt
# Take the JWT from cookies, verify it, attach the user to the socket
@database_sync_to_async
def get_user(user_id):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser

    User = get_user_model()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser

        headers = dict(scope.get("headers", [])) # Get headers from scope
        cookies = headers.get(b"cookie", b"").decode() # Decode cookies

        token = None
        for part in cookies.split(";"):
            if part.strip().startswith("access_token="): # Look for access_token cookie
                token = part.split("=", 1)[1] # Extract token value

        if not token:
            scope["user"] = AnonymousUser()
            return await self.inner(scope, receive, send)

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            scope["user"] = await get_user(payload["user_id"])
        except Exception:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
