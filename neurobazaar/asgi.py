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
    # Basic histogram WebSocket routes
    re_path(r"^histogram\d+/ws/?$", MultiPortWebSocketProxy.as_asgi()),
    
    # General histogram WebSocket routes
    re_path(r"^histogramgeneral\d+/ws/?$", MultiPortWebSocketProxy.as_asgi()),
    
    # OoD analyzer WebSocket routes
    re_path(r"^oodanalyzer\d+/ws/?$", MultiPortWebSocketProxy.as_asgi()),
    
    # Generic WebSocket routes
    re_path(r"^ws/(?P<port>\d+)/?$", MultiPortWebSocketProxy.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": ASGIStaticFilesHandler(django_asgi_app),
    "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
