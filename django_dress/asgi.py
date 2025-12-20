import os
# Daphne starts Django outside of manage.py.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_dress.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from order.routing import websocket_urlpatterns
from order.ws_middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(), # normal HTTP requests
    "websocket": URLRouter(websocket_urlpatterns),

})
