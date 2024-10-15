from wslink.protocol import ServerProtocol

class CustomServerProtocol(ServerProtocol):
    async def onClose(self, client_id):
        if client_id in self.unchunkers:
            del self.unchunkers[client_id]
        if client_id in self.clients:
            del self.clients[client_id]
        for k, v in self.subscriptions.items():
            if client_id in v:
                v.remove(client_id)