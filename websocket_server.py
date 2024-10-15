import asyncio
from aiohttp import web, ClientSession

async def websocket_handler(request):
    ws_server = web.WebSocketResponse()
    await ws_server.prepare(request)

    async with ClientSession() as session:
        async with session.ws_connect('ws://localhost:5459/ws') as ws_client:
            async for msg in ws_server:
                if msg.type == web.WSMsgType.TEXT:
                    await ws_client.send_str(msg.data)
                elif msg.type == web.WSMsgType.BINARY:
                    await ws_client.send_bytes(msg.data)
                elif msg.type == web.WSMsgType.CLOSE:
                    await ws_client.close()

                async for msg in ws_client:
                    if msg.type == web.WSMsgType.TEXT:
                        await ws_server.send_str(msg.data)
                    elif msg.type == web.WSMsgType.BINARY:
                        await ws_server.send_bytes(msg.data)
                    elif msg.type == web.WSMsgType.CLOSE:
                        await ws_server.close()

    return ws_server

app = web.Application()
app.router.add_get('/trame-proxy/ws', websocket_handler)

if __name__ == '__main__':
    web.run_app(app, port=8000)