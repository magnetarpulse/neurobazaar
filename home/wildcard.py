import asyncio
import websockets
import json
import logging
import ssl
from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps
from asgiref.sync import sync_to_async
from home.models import UpstreamServer, ServerInstance

logger = logging.getLogger(__name__)

class MultiPortWebSocketProxy(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.upstream_connections = {}
        connect_tasks = []

        # Get the port from URL if provided
        port = self.scope['url_route']['kwargs'].get('port')
        
        if port:
            # Direct port connection
            server_instance = await self.get_server_instance(port)
            if server_instance:
                connect_tasks.append(self.connect_to_upstream(server_instance.ip, server_instance.port))
        else:
            # Route-based connection (legacy support)
            route = self.scope['url_route']['kwargs'].get('route', 'new')
            upstream_servers = await self.get_upstream_servers(route)
            for server in upstream_servers:
                connect_tasks.append(self.connect_to_upstream(server.ip, server.port))

        await asyncio.gather(*connect_tasks)

    @sync_to_async
    def get_server_instance(self, port):
        try:
            return ServerInstance.objects.get(port=port, is_running=True)
        except ServerInstance.DoesNotExist:
            logger.error(f"No running server instance found for port {port}")
            return None

    @sync_to_async
    def get_upstream_servers(self, route):
        return list(UpstreamServer.objects.filter(route=route))

    async def connect_to_upstream(self, ip, port):
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            ws = await websockets.connect(
                f'wss://{ip}:{port}/ws',
                open_timeout=5,
                close_timeout=5,
                ssl=ssl_context
            )
            self.upstream_connections[(ip, port)] = ws
            asyncio.create_task(self.receive_from_upstream(ip, port))
            logger.info(f"WebSocket connection established to {ip}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to upstream {ip}:{port}: {str(e)}")

    async def disconnect(self, close_code):
        disconnect_tasks = [ws.close() for ws in self.upstream_connections.values()]
        await asyncio.gather(*disconnect_tasks)
        logger.info(f"All WebSocket connections closed with code: {close_code}")

    async def receive(self, text_data=None, bytes_data=None):
        send_tasks = []
        for (ip, port), ws in self.upstream_connections.items():
            if text_data:
                logger.info(f"Sending text message to upstream {ip}:{port}: {text_data}")
                send_tasks.append(ws.send(text_data))
            elif bytes_data:
                logger.info(f"Sending binary message to upstream {ip}:{port}: {len(bytes_data)} bytes")
                send_tasks.append(ws.send(bytes_data))
        
        await asyncio.gather(*send_tasks)

    async def receive_from_upstream(self, ip, port):
        ws = self.upstream_connections[(ip, port)]
        try:
            while True:
                message = await ws.recv()
                if isinstance(message, str):
                    logger.info(f"Received text message from upstream {ip}:{port}: {message}")
                    try:
                        data = json.loads(message)
                        if 'clientID' not in data and 'id' in data:
                            data['clientID'] = data['id']
                        message = json.dumps(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON message from {ip}:{port}: {message}")
                    await self.send(text_data=message)
                else:
                    logger.info(f"Received binary message from upstream {ip}:{port}: {len(message)} bytes")
                    await self.send(bytes_data=message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Upstream connection closed for {ip}:{port}")

    async def send(self, text_data=None, bytes_data=None):
        if text_data:
            logger.info(f"Sending text message to client: {text_data}")
        elif bytes_data:
            logger.info(f"Sending binary message to client: {len(bytes_data)} bytes")
        await super().send(text_data=text_data, bytes_data=bytes_data)
