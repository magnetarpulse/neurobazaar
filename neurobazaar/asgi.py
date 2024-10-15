import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from home.consumers import WebSocketProxy

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurobazaar.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter([
        re_path(r"^new/ws$", WebSocketProxy.as_asgi()),
    ]),
})
