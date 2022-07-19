#!/usr/bin/env python3

import asyncio
import uuid
import pak
import smo
from aioconsole import aprint

class MyProxy(smo.Proxy):
    pass

class MyClient(smo.Client):
    def __init__(self, *args, echo, **kwargs):
        super().__init__(*args, **kwargs)

        self.echo = echo

    async def _delay(self):
        await asyncio.sleep(0.5)

    async def _echo_packet(self, packet):
        copy = packet.copy()
        copy.client_id = self.client_id

        await self._delay()
        await self.write_packet_instance(copy)

    @pak.most_derived_packet_listener(smo.Packet)
    async def _echo(self, packet):
        if packet.client_id != self.echo:
            return

        await self._echo_packet(packet)

    @_echo.derived_listener(smo.PlayerConnectPacket)
    async def _echo(self, packet):
        return

    @_echo.derived_listener(smo.PlayerDisconnectPacket)
    async def _echo(self, packet):
        await aprint(packet)

    @_echo.derived_listener(smo.CaptureInfoPacket)
    async def _echo(self, packet):
        if packet.client_id != self.echo:
            return

        if packet.name == "":
            return

        # Report uncapture before new capture (since we might already be reporting we're still in a capture).
        await self._delay()
        await self.write_packet(smo.CaptureInfoPacket, name="")

        # Delay before writing real capture to help other clients update properly.
        await self._delay()
        await self.write_packet(smo.CaptureInfoPacket, name=packet.name)

class MyServer(smo.Server):
    @pak.packet_listener(smo.Packet)
    async def debug(self, client, packet):
        await aprint(packet)

def proxy():
    proxy = MyProxy("localhost", 1028)
    proxy.run()

def client():
    client = MyClient("localhost", name="Test", echo=uuid.UUID("99971006-3086-1000-9971-29670938e59c"), client_id=uuid.UUID("8ca3fcdd-2940-1000-b5f8-579301fcbfbb"))
    client.run()

def server():
    server = MyServer()
    server.run()

if __name__ == "__main__":
    client()
