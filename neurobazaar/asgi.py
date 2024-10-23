import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from channels.auth import AuthMiddlewareStack
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurobazaar.settings')
django.setup()

from home.wildcard import MultiPortWebSocketProxy

django_asgi_app = get_asgi_application()

websocket_urlpatterns = [
    re_path(r"^new/ws/?$", MultiPortWebSocketProxy.as_asgi(), {'route': 'new'}),
    re_path(r"^new2/ws/?$", MultiPortWebSocketProxy.as_asgi(), {'route': 'new2'}),
]

application = ProtocolTypeRouter({
    "http": ASGIStaticFilesHandler(django_asgi_app),
    "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
