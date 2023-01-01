import asyncio
import pak
from aioconsole import aprint

from .connection import Connection
from .packets    import Packet, PlayerConnectPacket

__all__ = [
    "Proxy",
]

class Proxy(pak.AsyncPacketHandler):
    class _Connection(Connection):
        # Used for the 'ServerConnection' and 'ClientConnection'
        # to depend on each other for closing.
        #
        # We make explicit calls to 'Connection' at times to avoid recursion.

        def __init__(self, proxy, *, destination=None, **kwargs):
            self.proxy       = proxy
            self.destination = destination

            super().__init__(**kwargs)

        def is_closing(self):
            return Connection.is_closing(self) or Connection.is_closing(self.destination)

        def close(self):
            Connection.close(self)
            Connection.close(self.destination)

        async def wait_closed(self):
            await Connection.wait_closed(self)
            await Connection.wait_closed(self.destination)

    class ServerConnection(_Connection):
        pass

    class ClientConnection(_Connection):
        def __init__(self, proxy, **kwargs):
            super().__init__(proxy, **kwargs)

            self.proxy.clients.append(self)

        def close(self):
            try:
                self.proxy.clients.remove(self)

            # We might already have been closed.
            except ValueError:
                pass

            super().close()

        @property
        def client_id(self):
            return self.destination.client_id

        @client_id.setter
        def client_id(self, value):
            self.destination.client_id = value

    def __init__(self, server_address, server_port=1027, *, host_address=None, host_port=1027):
        super().__init__()

        self.server_address = server_address
        self.server_port    = server_port

        self.host_address = host_address
        self.host_port    = host_port

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

    async def _listen_to_packet(self, source_conn, packet):
        async with self.listener_task_group(listen_sequentially=False) as group:
            listeners = self.listeners_for_packet(packet)
            async def proxy_wrapper():
                results = await asyncio.gather(*[listener(source_conn, packet) for listener in listeners])

                if False not in results:
                    await source_conn.destination.write_packet_instance(packet)

            group.create_task(proxy_wrapper())

    async def _listen_impl(self, source_conn):
        while self.is_serving() and not source_conn.is_closing():
            try:
                async for packet in source_conn.continuously_read_packets():
                    await self._listen_to_packet(source_conn, packet)

            finally:
                await self.end_listener_tasks()

    async def listen(self, client):
        await asyncio.gather(self._listen_impl(client), self._listen_impl(client.destination))

    async def new_connection(self, client_reader, client_writer):
        server_reader, server_writer = await self.open_streams()

        server = self.ServerConnection(self, reader=server_reader, writer=server_writer)
        client = self.ClientConnection(self, destination=server, reader=client_reader, writer=client_writer)

        server.destination = client

        async with client:
            await self.listen(client)

    async def open_server(self):
        return await asyncio.start_server(self.new_connection, self.host_address, self.host_port)

    async def open_streams(self):
        return await asyncio.open_connection(self.server_address, self.server_port)

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
            self.close()

    @pak.packet_listener(PlayerConnectPacket)
    async def _on_player_info(self, source, packet):
        source.client_id = packet.client_id
