import uuid
import numpy as np
import pak

__all__ = [
    "Uid",
    "Vector3f",
    "Quatf",
]

class Uid(pak.Type):
    _size    = 0x10
    _default = uuid.UUID(int=0)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return uuid.UUID(bytes_le=buf.read(0x10))

    @classmethod
    def _pack(cls, value, *, ctx):
        return value.bytes_le

class _Float32Array(pak.Type):
    _num_floats = None

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls._size    = 4 * cls._num_floats
        cls._default = np.array([0.0] * cls._num_floats)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return np.array([pak.Float32.unpack(buf, ctx=ctx) for x in range(cls._num_floats)])

    @classmethod
    def _pack(cls, value, *, ctx):
        return b"".join(pak.Float32.pack(value[x], ctx=ctx) for x in range(cls._num_floats))

class Vector3f(_Float32Array):
    _num_floats = 3

class Quatf(_Float32Array):
    _num_floats = 4
