__all__ = [
    "Connection",
]

import asyncio
import uuid
import pak

from .packets import Packet, GenericPacketWithID

class Connection(pak.io.Connection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, ctx=Packet.Context())

        self.client_id = uuid.UUID(int=0)

    def create_packet(self, packet_cls, *, client=None, **fields):
        if client is None:
            client = self

        return packet_cls(client_id=client.client_id, **fields, ctx=self.ctx)

    async def _read_next_packet(self):
        header_data = await self.read_data(Packet.Header.size(ctx=self.ctx))
        if header_data is None:
            return None

        header = Packet.Header.unpack(header_data)

        packet_data = await self.read_data(header.size)
        if packet_data is None:
            return None

        packet_cls = Packet.subclass_with_id(header.id, ctx=self.ctx)

        if packet_cls is None:
            packet_cls = GenericPacketWithID(header.id)

        packet           = packet_cls.unpack(packet_data, ctx=self.ctx)
        packet.client_id = header.client_id

        return packet

    async def write_packet_instance(self, packet):
        await self.write_data(packet.pack(ctx=self.ctx))
