import asyncio
import websockets
import json
import logging
import ssl
from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps
from asgiref.sync import sync_to_async
from home.models import UpstreamServer, ServerInstance
from urllib.parse import parse_qs
import re

logger = logging.getLogger(__name__)

class MultiPortWebSocketProxy(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.upstream_connections = {}
        
        # Extract route from the URL path
        path = self.scope['path']
        
        # Try to match new format (histogram1, analyzer1, histogramgeneral2, etc.)
        route_match = re.search(r'(histogram|histogramgeneral|analyzer)\d+', path)
        if route_match:
            self.section_type = route_match.group(0)  # This will get 'histogram1', 'histogramgeneral2', etc.
        else:
            # Try to match old format (basic, general, ood)
            if 'histogram' in path and 'general' not in path:
                self.section_type = 'basic'
            elif 'histogramgeneral' in path:
                self.section_type = 'general'
            elif 'oodanalyzer' in path:
                self.section_type = 'ood'
            else:
                self.section_type = None
        
        logger.info(f"Connecting to section type: {self.section_type}")
            
        # Get cookies from query string
        query_string = self.scope['query_string'].decode()
        cookies = parse_qs(query_string).get('cookies', [None])[0]
        
        if cookies:
            # Parse the cookies string and organize by server type
            self.cookies = {}
            for cookie in cookies.split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    # First try to match the exact route prefix
                    route_specific_match = False
                    for route_prefix in ['histogram', 'histogramgeneral', 'analyzer']:
                        if name.startswith(f"{self.section_type}_"):
                            if self.section_type not in self.cookies:
                                self.cookies[self.section_type] = {}
                            cookie_name = name[len(self.section_type) + 1:]  # +1 for the underscore
                            self.cookies[self.section_type][cookie_name] = value
                            route_specific_match = True
                            break
                    
                    # If no route-specific match, try the old format prefixes
                    if not route_specific_match:
                        if name.startswith('basic_') and (self.section_type == 'basic' or 'histogram' in self.section_type):
                            if self.section_type not in self.cookies:
                                self.cookies[self.section_type] = {}
                            self.cookies[self.section_type][name[6:]] = value
                        elif name.startswith('general_') and (self.section_type == 'general' or 'histogramgeneral' in self.section_type):
                            if self.section_type not in self.cookies:
                                self.cookies[self.section_type] = {}
                            self.cookies[self.section_type][name[8:]] = value
                        elif name.startswith('ood_') and (self.section_type == 'ood' or 'analyzer' in self.section_type):
                            if self.section_type not in self.cookies:
                                self.cookies[self.section_type] = {}
                            self.cookies[self.section_type][name[4:]] = value
                        else:
                            # Store the cookie as is if it doesn't match any prefix
                            if self.section_type not in self.cookies:
                                self.cookies[self.section_type] = {}
                            self.cookies[self.section_type][name] = value
        else:
            self.cookies = {}
            
        logger.info(f"Processed cookies for section {self.section_type}: {self.cookies}")

        # Get the port from URL if provided
        port = self.scope['url_route']['kwargs'].get('port')
        
        if port:
            # Direct port connection
            server_instance = await self.get_server_instance(port)
            if server_instance:
                await self.connect_to_upstream(server_instance.ip, server_instance.port, server_instance.server_type)
        else:
            # Route-based connection using the exact route from the URL
            if self.section_type:
                logger.info(f"Looking for upstream servers with route: {self.section_type}")
                upstream_servers = await self.get_upstream_servers(self.section_type)
                if not upstream_servers:
                    logger.error(f"No upstream servers found for route: {self.section_type}")
                for server in upstream_servers:
                    logger.info(f"Connecting to upstream server: {server.ip}:{server.port} for route {server.route}")
                    await self.connect_to_upstream(server.ip, server.port, server.route)
            else:
                logger.error(f"No valid route found in URL path: {path}")

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

    async def connect_to_upstream(self, ip, port, server_type):
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create connection parameters
            connect_kwargs = {
                'ssl': ssl_context,
                'open_timeout': 5,
                'close_timeout': 5,
            }
            
            # Add headers only if cookies exist for this server type
            if self.cookies and server_type in self.cookies:
                cookie_str = '; '.join([f"{k}={v}" for k, v in self.cookies[server_type].items()])
                connect_kwargs['header'] = [
                    ('Cookie', cookie_str)
                ]
                logger.info(f"Using cookies for {server_type}: {cookie_str}")
            
            ws = await websockets.connect(
                f'wss://{ip}:{port}/ws',
                **connect_kwargs
            )
            self.upstream_connections[(ip, port)] = ws
            asyncio.create_task(self.receive_from_upstream(ip, port))
            logger.info(f"WebSocket connection established to {ip}:{port} for section {self.section_type}")
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
                try:
                    # Parse the message to add section type if it's JSON
                    data = json.loads(text_data)
                    data['section_type'] = self.section_type
                    modified_text_data = json.dumps(data)
                    logger.info(f"Sending text message to upstream {ip}:{port}: {modified_text_data}")
                    send_tasks.append(ws.send(modified_text_data))
                except json.JSONDecodeError:
                    # If not JSON, send as is
                    logger.info(f"Sending non-JSON text message to upstream {ip}:{port}: {text_data}")
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
                    try:
                        data = json.loads(message)
                        # Add clientID if missing
                        if 'clientID' not in data and 'id' in data:
                            data['clientID'] = data['id']
                        # Add section type to response
                        data['section_type'] = self.section_type
                        message = json.dumps(data)
                        logger.info(f"Received text message from upstream {ip}:{port}: {message}")
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON message from {ip}:{port}: {message}")
                    await self.send(text_data=message)
                else:
                    logger.info(f"Received binary message from upstream {ip}:{port}: {len(message)} bytes")
                    await self.send(bytes_data=message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Upstream connection closed for {ip}:{port}")
        except Exception as e:
            logger.error(f"Error in receive_from_upstream for {ip}:{port}: {str(e)}")

    async def send(self, text_data=None, bytes_data=None):
        if text_data:
            logger.info(f"Sending text message to client: {text_data}")
        elif bytes_data:
            logger.info(f"Sending binary message to client: {len(bytes_data)} bytes")
        await super().send(text_data=text_data, bytes_data=bytes_data)
