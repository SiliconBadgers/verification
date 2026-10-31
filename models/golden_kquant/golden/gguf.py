"""Minimal GGUF (v2/v3) reader: metadata, tensor table and raw tensor rows.

Format as written by ggml (ggml/src/gguf.cpp at llama.cpp f46bc30): little-endian header
"GGUF", version, tensor count, metadata count; key/value pairs; tensor infos (name, dims,
type, offset); then the data section, aligned to general.alignment (default 32). A tensor's
ne[0] is its contiguous (reduction) dimension; a row is ne[0] elements.
"""

import struct

from .blocks import TYPE_BY_ID, TYPES

_SCALARS = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?",
            10: "<Q", 11: "<q", 12: "<d"}
_STRING, _ARRAY = 8, 9


class Tensor:
    def __init__(self, name, dims, type_id, offset):
        self.name = name
        self.dims = dims  # ggml order: ne[0] first
        self.type_id = type_id
        self.offset = offset  # relative to the data section

    @property
    def type_name(self):
        return TYPE_BY_ID.get(self.type_id, f"type{self.type_id}")

    @property
    def row_bytes(self):
        _, per_block, size = TYPES[self.type_name]
        return self.dims[0] // per_block * size

    @property
    def rows(self):
        n = 1
        for d in self.dims[1:]:
            n *= d
        return n


class GGUF:
    def __init__(self, path):
        self.path = path
        self.metadata = {}
        self.tensors = {}
        with open(path, "rb") as f:
            self._f = f
            if f.read(4) != b"GGUF":
                raise ValueError(f"{path}: not a GGUF file")
            (self.version,) = self._u("<I")
            if self.version not in (2, 3):
                raise ValueError(f"{path}: GGUF version {self.version} is not supported")
            n_tensors, n_kv = self._u("<QQ")
            for _ in range(n_kv):
                key = self._string()
                (vtype,) = self._u("<I")
                self.metadata[key] = self._value(vtype)
            for _ in range(n_tensors):
                name = self._string()
                (n_dims,) = self._u("<I")
                dims = list(self._u(f"<{n_dims}Q"))
                type_id, offset = self._u("<IQ")
                self.tensors[name] = Tensor(name, dims, type_id, offset)
            align = int(self.metadata.get("general.alignment", 32))
            pos = f.tell()
            self.data_start = (pos + align - 1) // align * align
            del self._f

    def _u(self, fmt):
        s = struct.Struct(fmt)
        return s.unpack(self._f.read(s.size))

    def _string(self):
        (n,) = self._u("<Q")
        return self._f.read(n).decode("utf-8", errors="replace")

    def _value(self, vtype):
        if vtype in _SCALARS:
            return self._u(_SCALARS[vtype])[0]
        if vtype == _STRING:
            return self._string()
        if vtype == _ARRAY:
            etype, count = self._u("<IQ")
            if etype in _SCALARS:
                fmt = _SCALARS[etype]
                size = struct.calcsize(fmt)
                return list(struct.unpack(f"<{count}{fmt[1]}", self._f.read(size * count)))
            return [self._value(etype) for _ in range(count)]
        raise ValueError(f"unknown GGUF value type {vtype}")

    def read_rows(self, name, first, count):
        """Raw bytes of rows first .. first + count - 1 of a tensor."""
        t = self.tensors[name]
        if first < 0 or first + count > t.rows:
            raise IndexError(f"{name} has {t.rows} rows")
        with open(self.path, "rb") as f:
            f.seek(self.data_start + t.offset + first * t.row_bytes)
            return f.read(count * t.row_bytes)
