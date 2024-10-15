import asyncio
import websockets
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class WebSocketProxy(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.ws = await websockets.connect('ws://localhost:5459/ws')
        logger.info("WebSocket connection established")
        asyncio.create_task(self.receive_from_upstream())

    async def disconnect(self, close_code):
        await self.ws.close()
        logger.info(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            logger.info(f"Received text message from client: {text_data}")
            await self.ws.send(text_data)
        elif bytes_data:
            logger.info(f"Received binary message from client: {len(bytes_data)} bytes")
            await self.ws.send(bytes_data)

    async def receive_from_upstream(self):
        try:
            while True:
                message = await self.ws.recv()
                if isinstance(message, str):
                    logger.info(f"Received text message from upstream: {message}")
                    try:
                        data = json.loads(message)
                        if 'clientID' not in data and 'id' in data:
                            data['clientID'] = data['id']
                        message = json.dumps(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON message: {message}")
                    await self.send(text_data=message)
                else:
                    logger.info(f"Received binary message from upstream: {len(message)} bytes")
                    await self.send(bytes_data=message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Upstream connection closed")

    async def send(self, text_data=None, bytes_data=None):
        if text_data:
            logger.info(f"Sending text message to client: {text_data}")
        elif bytes_data:
            logger.info(f"Sending binary message to client: {len(bytes_data)} bytes")
        await super().send(text_data=text_data, bytes_data=bytes_data)
