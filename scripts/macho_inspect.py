"""Minimal read-only Mach-O helpers for the local ARM64 investigation."""
import bisect
import struct
from pathlib import Path


class MachO:
    def __init__(self, path, arch='arm64'):
        self.path = Path(path)
        self.raw = self.path.read_bytes()
        cpu = {'arm64': 0x100000c, 'x86_64': 0x1000007}[arch]
        self.base = 0
        if self.raw[:4] == b'\xca\xfe\xba\xbe':
            count = struct.unpack_from('>I', self.raw, 4)[0]
            for i in range(count):
                cputype, _, offset, size, _ = struct.unpack_from('>IIIII', self.raw, 8+20*i)
                if cputype == cpu:
                    self.base = offset
                    break
            else:
                raise ValueError('Architecture not found')
        self.data = self.raw[self.base:]
        assert self.data[:4] == b'\xcf\xfa\xed\xfe', 'Expected 64-bit little-endian Mach-O'
        assert struct.unpack_from('<I', self.data, 4)[0] == cpu
        ncmds = struct.unpack_from('<I', self.data, 16)[0]
        pos = 32
        self.segments = []
        self.sections = {}
        starts = None
        for _ in range(ncmds):
            cmd, size = struct.unpack_from('<II', self.data, pos)
            if cmd == 0x19:
                name, va, vs, fo, fs, _, _, nsects, _ = struct.unpack_from('<16sQQQQIIII', self.data, pos+8)
                name = name.rstrip(b'\0').decode()
                self.segments.append((name, va, vs, fo, fs))
                if name == '__TEXT':
                    self.text_base = va
                for i in range(nsects):
                    off = pos+72+80*i
                    sn, sg, addr, length, offset = struct.unpack_from('<16s16sQQI', self.data, off)
                    self.sections[(sg.rstrip(b'\0').decode(), sn.rstrip(b'\0').decode())] = (addr, length, offset)
            elif cmd == 0x26:
                starts = struct.unpack_from('<II', self.data, pos+8)
            pos += size
        self.functions = []
        if starts:
            p, length = starts
            end = p+length
            address = self.text_base
            while p < end:
                number = shift = 0
                while True:
                    byte = self.data[p]
                    p += 1
                    number |= (byte & 127) << shift
                    shift += 7
                    if byte < 128:
                        break
                if not number:
                    break
                address += number
                self.functions.append(address)

    def offset(self, address):
        for _, va, _, offset, size in self.segments:
            if va <= address < va+size:
                return offset+address-va
        raise ValueError(hex(address))

    def read(self, address, size):
        off = self.offset(address)
        return self.data[off:off+size]

    def cstring(self, address):
        off = self.offset(address)
        return self.data[off:self.data.index(0, off)].decode(errors='replace')

    def function(self, address):
        i = bisect.bisect_right(self.functions, address)-1
        return self.functions[i], self.functions[i+1]
