"""Brand build 830 MCP registration names, including add/check/remove operations.

Only the MCP configuration dictionary and MCPAgentSetup code are changed.
Swift small-string payload and length discriminator are patched together.
"""
import hashlib
from pathlib import Path
from macho_inspect import MachO

SOURCE_SHA256 = '2cc0ac62d6f78848a69c1254bea6c8a15ea707f5af725df1a61e0734508db23d'
# architecture, virtual address, original bytes, replacement bytes
EDITS = (
    ('arm64', 0x10054b954, '8a2e8cd24a8cadf2aa0ccef28aadeef2', '8a2a8cd24a8cadf2aa6cc8f24a2eecf2'),
    ('arm64', 0x10054d314, '882e8cd2488cadf2a80ccef288adeef2', '882a8cd2488cadf2a86cc8f2482eecf2'),
    ('arm64', 0x100576ff8, '802e8cd2408cadf2a00ccef280adeef2', '802a8cd2408cadf2a06cc8f2402eecf2'),
    ('arm64', 0x100577b2c, '992e8cd2598cadf2b90ccef299adeef2', '992a8cd2598cadf2b96cc8f2592eecf2'),
    ('arm64', 0x100577e34, '932e8cd2538cadf2b30ccef293adeef2', '932a8cd2538cadf2b36cc8f2532eecf2'),
    ('arm64', 0x10054b968, '6a0e80d20a20fdf2', 'ca8c8ed20a40fdf2'),
    ('arm64', 0x10054d324, '690e80d20920fdf2', 'c98c8ed20940fdf2'),
    ('arm64', 0x100577008, '610e80d20120fdf2', 'c18c8ed20140fdf2'),
    ('arm64', 0x100577b8c, '610e80d20120fdf2', 'c18c8ed20140fdf2'),
    ('arm64', 0x100577e98, '610e80d20120fdf2', 'c18c8ed20140fdf2'),
    ('arm64', 0x100577edc, '610e80d20120fdf2', 'c18c8ed20140fdf2'),
    ('arm64', 0x100577f64, '620e80d20220fdf2', 'c28c8ed20240fdf2'),
    ('arm64', 0x1005780d0, '610e80d20120fdf2', 'c18c8ed20140fdf2'),
    ('arm64', 0x1005781dc, '610e80d20120fdf2', 'c18c8ed20140fdf2'),
    ('x86_64', 0x1005dae94, '7461626c65706c75', '5461626c65437261'),
    ('x86_64', 0x1005daea2, '73000000000000e9', '66740000000000ea'),
    ('x86_64', 0x1005dcbc9, '7461626c65706c75', '5461626c65437261'),
    ('x86_64', 0x1005dcbd7, '73000000000000e9', '66740000000000ea'),
    ('x86_64', 0x10060c08e, '7461626c65706c75', '5461626c65437261'),
    ('x86_64', 0x10060c098, '73000000000000e9', '66740000000000ea'),
    ('x86_64', 0x10060cba9, '7461626c65706c75', '5461626c65437261'),
    ('x86_64', 0x10060cf0f, '7461626c65706c75', '5461626c65437261'),
    ('x86_64', 0x10060d01e, '7461626c65706c75', '5461626c65437261'),
    ('x86_64', 0x10060cbf6, '73000000000000e9', '66740000000000ea'),
    ('x86_64', 0x10060cf66, '73000000000000e9', '66740000000000ea'),
    ('x86_64', 0x10060cf93, '73000000000000e9', '66740000000000ea'),
    ('x86_64', 0x10060d02e, '73000000000000e9', '66740000000000ea'),
    ('x86_64', 0x10060d1b6, '73000000000000e9', '66740000000000ea'),
    ('x86_64', 0x10060d2ba, '73000000000000e9', '66740000000000ea'),
)


def edits():
    return [(arch, address, bytes.fromhex(before), bytes.fromhex(after))
            for arch, address, before, after in EDITS]


def state(bundle):
    binary=Path(bundle)/'Contents/MacOS/TablePlus'
    slices={arch:MachO(binary,arch) for arch in ('arm64','x86_64')}
    current=[slices[arch].read(address,len(before)) for arch,address,before,_ in edits()]
    if all(actual==after for actual,(_,_,_,after) in zip(current,edits())):return 'TableCraft'
    if all(actual==before for actual,(_,_,before,_) in zip(current,edits())):return 'TablePlus'
    raise ValueError('Incomplete or unsupported MCP registration strings')


def patch(bundle):
    bundle=Path(bundle);binary=bundle/'Contents/MacOS/TablePlus'
    if bundle.is_symlink() or binary.is_symlink() or binary.resolve()==Path('/Applications/TablePlus.app/Contents/MacOS/TablePlus').resolve():
        raise ValueError('Only a separate non-symlink copy may be modified')
    if state(bundle)=='TableCraft':return []
    raw=binary.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise ValueError('Unsupported executable SHA-256')
    slices={arch:MachO(binary,arch) for arch in ('arm64','x86_64')}
    data=bytearray(raw);changes=[]
    for arch,address,before,after in edits():
        macho=slices[arch];offset=macho.base+macho.offset(address)
        if len(before)!=len(after) or data[offset:offset+len(before)]!=before:
            raise ValueError('Unexpected MCP registration bytes; nothing written')
        data[offset:offset+len(before)]=after
        changes.append(dict(architecture=arch,address=hex(address),file_offset=offset,before=before.hex(),after=after.hex()))
    binary.write_bytes(data)
    if state(bundle)!='TableCraft':raise ValueError('MCP registration verification failed')
    return changes
