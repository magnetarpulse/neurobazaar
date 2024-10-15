import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from home.consumers import WebSocketProxy
from channels.auth import AuthMiddlewareStack
from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurobazaar.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": ASGIStaticFilesHandler(django_asgi_app),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            re_path(r"^new/ws$", WebSocketProxy.as_asgi()),
        ])
    ),
})
