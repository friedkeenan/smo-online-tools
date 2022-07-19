import enum

__all__ = [
    "ConnectionType",
]

class ConnectionType(enum.Enum):
    Init      = 0
    Reconnect = 1
