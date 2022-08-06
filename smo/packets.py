import uuid
import pak

from . import types
from . import enums

__all__ = [
    "Packet",
    "InitPacket",
    "PlayerInfoPacket",
    "CappyInfoPacket",
    "GameInfoPacket",
    "TagInfoPacket",
    "PlayerConnectPacket",
    "PlayerDisconnectPacket",
    "CostumeInfoPacket",
    "ShineCollectPacket",
    "CaptureInfoPacket",
    "ChangeStagePacket",
    "ServerCommandPacket",
]

_PlayerAnim = pak.Enum(pak.Int16, enums.PlayerAnim)

class Packet(pak.Packet):
    class Header(pak.Packet.Header):
        client_id: types.Uid
        id:        pak.Int16
        size:      pak.Int16

    def __init__(self, *, client_id, ctx=None, **fields):
        super().__init__(ctx=ctx, **fields)

        self.client_id = client_id

    def __repr__(self):
        return "".join([
            f"{type(self).__qualname__}(",

            ", ".join([
                f"client_id={repr(self.client_id)}",

                *(f"{name}={repr(value)}" for name, value in self.enumerate_field_values()),
            ]),

            ")"
        ])

class GenericPacket(Packet):
    data: pak.RawByte[None]

@pak.util.cache
def GenericPacketWithID(id):
    return type(f"GenericPacketWithID({id})", (GenericPacket,), dict(
        id = id,
    ))

class InitPacket(Packet):
    id = 1

    max_players: pak.UInt16

class PlayerInfoPacket(Packet):
    id = 2

    position:           types.Vector3f
    rotation:           types.Quatf
    anim_blend_weights: pak.Float32[6]
    act_name:           _PlayerAnim
    sub_act_name:       _PlayerAnim

class CappyInfoPacket(Packet):
    id = 3

    position:  types.Vector3f
    rotation:  types.Quatf
    visible:   pak.Bool
    anim_name: pak.StaticString(0x30)

    # There is some alignment padding
    # at the end of the packet due to
    # a bug in the vanilla client.
    _alignment_padding: pak.Padding[3]

class GameInfoPacket(Packet):
    id = 4

    is_2d:        pak.Bool
    scenario_num: pak.UInt8
    stage_name:   pak.StaticString(0x40)

class TagInfoPacket(Packet):
    id = 5

    update_type: pak.BitMask(
        "UpdateType",
        pak.UInt8,

        time  = 0,
        state = 1,
    )

    is_it:   pak.Bool
    seconds: pak.UInt8
    minutes: pak.UInt16

class PlayerConnectPacket(Packet):
    id = 6

    type:        pak.Enum(pak.Int32, enums.ConnectionType)
    max_players: pak.Defaulted(pak.UInt16, 0xFFFF)
    name:        pak.StaticString(0x20)

class PlayerDisconnectPacket(Packet):
    id = 7

class CostumeInfoPacket(Packet):
    id = 8

    body_model: pak.StaticString(0x20)
    cap_model:  pak.StaticString(0x20)

class ShineCollectPacket(Packet):
    id = 9

    shine_id: pak.Int32
    is_grand: pak.Bool

class CaptureInfoPacket(Packet):
    id = 10

    name: pak.StaticString(0x20)

class ChangeStagePacket(Packet):
    id = 11

    change_stage:      pak.StaticString(0x30)
    change_id:         pak.StaticString(0x10)
    scenario_num:      pak.Int8
    sub_scenario_type: pak.UInt8

class ServerCommandPacket(Packet):
    id = 12

    command: pak.StaticString(0x30)
