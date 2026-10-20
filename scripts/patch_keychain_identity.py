#!/usr/bin/env python3
"""Isolate the exact 830 bundle's generic-password namespace; never access Keychain data."""
import hashlib
from pathlib import Path
import plistlib
import struct

from macho_inspect import MachO

SERVICE = 'com.tablecraft.TableCraft'
LABEL = 'TableCraft'
OLD_SERVICE = b'com.tableplus.TablePlus'
# Signed customized runtime, original 830, and the existing full-override unsigned 830.
SUPPORTED_SHA256 = {
    '4f26418e0178fd2448de1fd87ec2d36145107430ccb39df34cf176d89187e12c',
    '8e18e7010a4714e8e8e900db2cb9e82f876438b6936d5d7b9fa2db679d895ef7',
    '8f9a37ce5dfa8c0b606ccab1fb9394dffe2a8e4be9d5d7463c3a9d951e63f8f0',
}


def mov_wide(register, value, shift=0, keep=False):
    return struct.pack('<I', (0xf2800000 if keep else 0xd2800000)
                       | ((shift//16) << 21) | (value << 5) | register)


def edits():
    """Return exact (architecture, VA, before, after) edits; all sizes are unchanged."""
    result = []
    for arch, address in (('arm64', 0x100d95e50), ('x86_64', 0x100e87f80)):
        # Swift string storage has 8 zero bytes after the old string. Use two of them.
        result.append((arch, address, OLD_SERVICE.ljust(32, b'\0'), SERVICE.encode().ljust(32, b'\0')))
    for address, register in ((0x10000c438, 0), (0x1008077a4, 9), (0x100a0d104, 9),
                              (0x100a0d2ac, 9), (0x100a0d37c, 9), (0x100a0d3bc, 9)):
        result.append(('arm64', address, mov_wide(register, 23), mov_wide(register, 25)))
    # The adjacent instructions still mark these as native Swift large strings.
    for address, register in ((0x10000d1c8, 0), (0x1008ef616, 1), (0x100b3d61f, 1),
                              (0x100b3d7d1, 1), (0x100b3d8f2, 1), (0x100b3d94b, 1)):
        prefix = bytes((0x48, 0xb8+register))
        result.append(('x86_64', address, prefix+struct.pack('<Q', 0xd000000000000017),
                       prefix+struct.pack('<Q', 0xd000000000000019)))
    # Only kSecAttrLabel in KeychainSwift's save path; no global name replacement.
    for address, register, before, after, shift, keep in (
        (0x100a0d63c, 8, 0x5065, 0x4365, 32, True),
        (0x100a0d640, 8, 0x756c, 0x6172, 48, True),
        (0x100a0d644, 9, 0x73, 0x7466, 0, False),
        (0x100a0d648, 9, 0xe900, 0xea00, 48, True),
    ):
        result.append(('arm64', address, mov_wide(register, before, shift, keep),
                       mov_wide(register, after, shift, keep)))
    for address, before, after in ((0x100b3dbbf, 0x756c50656c626154, 0x617243656c626154),
                                   (0x100b3dbcd, 0xe900000000000073, 0xea00000000007466)):
        result.append(('x86_64', address, b'\x48\xb8'+struct.pack('<Q', before),
                       b'\x48\xb8'+struct.pack('<Q', after)))
    return result


def identity(bundle):
    binary = Path(bundle)/'Contents/MacOS/TablePlus'
    slices = {arch: MachO(binary, arch) for arch in ('arm64', 'x86_64')}
    current = [slices[arch].read(address, len(before)) for arch, address, before, _ in edits()]
    if all(actual == before for actual, (_, _, before, _) in zip(current, edits())):
        return 'legacy'
    if all(actual == after for actual, (_, _, _, after) in zip(current, edits())):
        return 'isolated'
    raise ValueError('Keychain identity is incomplete or this executable is unsupported')


def patch(bundle):
    bundle = Path(bundle)
    binary = bundle/'Contents/MacOS/TablePlus'
    if bundle.is_symlink() or binary.is_symlink() or binary.resolve() == Path('/Applications/TablePlus.app/Contents/MacOS/TablePlus').resolve():
        raise ValueError('Only a separate, non-symlink copy may be modified')
    info = plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
    if info.get('CFBundleVersion') != '830':
        raise ValueError('Keychain isolation requires exactly build 830')
    if identity(bundle) == 'isolated':
        return []
    raw = binary.read_bytes()
    if hashlib.sha256(raw).hexdigest() not in SUPPORTED_SHA256:
        raise ValueError('Unsupported executable SHA-256; no files changed')
    data = bytearray(raw)
    slices = {arch: MachO(binary, arch) for arch in ('arm64', 'x86_64')}
    changes = []
    for arch, address, before, after in edits():
        macho = slices[arch]
        offset = macho.base+macho.offset(address)
        if data[offset:offset+len(before)] != before or len(before) != len(after):
            raise ValueError('Unexpected bytes at {} {:#x}; no files changed'.format(arch, address))
        data[offset:offset+len(before)] = after
        changes.append(dict(architecture=arch, address=hex(address), file_offset=offset,
                            before=before.hex(), after=after.hex()))
    binary.write_bytes(data)
    if identity(bundle) != 'isolated':
        raise ValueError('Patched identity verification failed')
    return changes
