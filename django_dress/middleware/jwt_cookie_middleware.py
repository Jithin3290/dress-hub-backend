from django.utils.deprecation import MiddlewareMixin

class JWTAuthCookieMiddleware(MiddlewareMixin):
    COOKIE_NAMES = ("access_token", "access", "jwt_access")

    def process_request(self, request):
        for name in self.COOKIE_NAMES:
            token = request.COOKIES.get(name)
            if token:
                request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
                break
        return None
