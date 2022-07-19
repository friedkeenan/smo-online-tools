import asyncio
import pak

from .connection import Connection
from .packets import (
    Packet,
    InitPacket,
    PlayerConnectPacket,
    PlayerDisconnectPacket,
    GameInfoPacket,
    CostumeInfoPacket,
    ServerCommandPacket,
    ShineCollectPacket,
)

__all__ = [
    "Server",
]

class Server(pak.AsyncPacketHandler):
    class Connection(Connection):
        def __init__(self, server, **kwargs):
            super().__init__(**kwargs)

            self.server = server
            self.server.clients.append(self)

            self.name = None

            self.game_info    = None
            self.costume_info = None

        @property
        def connected(self):
            return self.name is not None

        async def wait_closed(self):
            await self.server.on_disconnect(self)

            await super().wait_closed()

        async def broadcast_packet(self, packet_cls, **fields):
            packet = self.create_packet(packet_cls, **fields)

            await self.broadcast_packet_instance(packet)

        async def broadcast_packet_instance(self, packet):
            for other_client in self.server.connected_clients:
                if other_client is self:
                    continue

                await other_client.write_packet_instance(packet)

    def __init__(self, *, address=None, port=1027, max_players=8):
        super().__init__()

        self.address = address
        self.port    = port

        self.max_players = max_players

        self.srv     = None
        self.clients = []

    def is_serving(self):
        return self.srv is not None and self.srv.is_serving()

    def close(self):
        if self.srv is None:
            return

        self.srv.close()

    async def wait_closed(self):
        if self.srv is None:
            return

        await self.srv.wait_closed()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        self.close()
        await self.wait_closed()

    async def _listen_to_packet(self, client, packet):
        async with self.listener_task_context(listen_sequentially=not client.connected):
            for listener in self.listeners_for_packet(packet):
                self.create_listener_task(listener(client, packet))

    async def listen(self, client):
        while self.is_serving() and not client.is_closing():
            try:
                async for packet in client.continuously_read_packets():
                    await self._listen_to_packet(client, packet)

            finally:
                await self.end_listener_tasks()

    async def new_connection(self, reader, writer):
        async with self.Connection(self, reader=reader, writer=writer) as client:
            await client.write_packet(
                InitPacket,

                max_players = self.max_players,
            )

            await self.listen(client)

    async def open_server(self):
        return await asyncio.start_server(self.new_connection, self.address, self.port)

    async def startup(self):
        self.srv = await self.open_server()

    async def on_start(self):
        await self.srv.serve_forever()

    async def start(self):
        await self.startup()

        async with self:
            await self.on_start()

    def run(self):
        try:
            asyncio.run(self.start())

        except KeyboardInterrupt:
            pass

    @property
    def connected_clients(self):
        return [client for client in self.clients if client.connected]

    async def on_disconnect(self, client):
        if client in self.clients:
            await client.broadcast_packet(PlayerDisconnectPacket)

            self.clients.remove(client)

    async def handle_command(self, client, command):
        pass

    @pak.most_derived_packet_listener(Packet)
    async def main_listener(self, client, packet):
        await client.broadcast_packet_instance(packet)

    @main_listener.derived_listener(PlayerConnectPacket)
    async def main_listener(self, client, packet):
        if len(self.connected_clients) >= self.max_players:
            client.close()
            await client.wait_closed()

            return

        client.client_id = packet.client_id
        client.name      = packet.name

        for other_client in self.connected_clients:
            if other_client is client:
                continue

            if other_client.game_info is not None:
                await client.write_packet_instance(other_client.game_info)

            await client.write_packet(
                PlayerConnectPacket,

                client      = other_client,
                max_players = self.max_players,
                name        = other_client.name,
            )

            if other_client.costume_info is not None:
                await client.write_packet_instance(other_client.costume_info)

    @main_listener.derived_listener(GameInfoPacket)
    async def main_listener(self, client, packet):
        client.game_info = packet

        await client.broadcast_packet_instance(packet)

    @main_listener.derived_listener(CostumeInfoPacket)
    async def main_listener(self, client, packet):
        client.costume_info = packet

        await client.broadcast_packet_instance(packet)

    @main_listener.derived_listener(ServerCommandPacket)
    async def main_listener(self, client, packet):
        await self.handle_command(client, packet.command)

    @main_listener.derived_listener(ShineCollectPacket)
    async def main_listener(self, client, packet):
        # The bare minimum server doesn't care about moons.
        pass
