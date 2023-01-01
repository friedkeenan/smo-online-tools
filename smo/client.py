import asyncio
import uuid
import pak

from . import enums
from .connection import Connection
from .packets import InitPacket, PlayerConnectPacket

__all__ = [
    "Client",
]

class Client(Connection, pak.AsyncPacketHandler):
    def __init__(self, address, port=1027, *, name, client_id, try_reconnecting=True):
        Connection.__init__(self)
        pak.AsyncPacketHandler.__init__(self)

        self.address = address
        self.port    = port

        self.name      = name
        self.client_id = client_id

        self.try_reconnecting = try_reconnecting
        self._connection_type = enums.ConnectionType.Init

    def register_packet_listener(self, coro_func, *packet_types, outgoing=False):
        return super().register_packet_listener(coro_func, *packet_types, outgoing=outgoing)

    async def write_packet_instance(self, packet):
        await super().write_packet_instance(packet)

        await self._listen_to_packet(packet, outgoing=True)

    async def _listen_to_packet(self, packet, *, outgoing):
        async with self.listener_task_group(listen_sequentially=self._listen_sequentially) as group:
            for listener in self.listeners_for_packet(packet, outgoing=outgoing):
                group.create_task(listener(packet))

    async def listen(self):
        try:
            async for packet in self.continuously_read_packets():
                await self._listen_to_packet(packet, outgoing=False)

        finally:
            await self.end_listener_tasks()

    async def open_streams(self):
        return await asyncio.open_connection(self.address, self.port)

    async def startup(self):
        self.reader, self.writer = await self.open_streams()

    async def on_start(self):
        self._listen_sequentially = True

        await self.listen()

    async def start(self):
        while True:
            await self.startup()

            async with self:
                await self.on_start()

            if not self.try_reconnecting:
                break

    def run(self):
        try:
            asyncio.run(self.start())

        except KeyboardInterrupt:
            self.close()

    @pak.packet_listener(InitPacket)
    async def _on_init(self, packet):
        self._listen_sequentially = False

        await self.write_packet(
            PlayerConnectPacket,

            type = self._connection_type,
            name = self.name,
        )

        self._connection_type = enums.ConnectionType.Reconnect

