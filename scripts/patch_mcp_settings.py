"""Update build 830 MCP settings paths/text without changing authentication or protocols."""
import hashlib
from pathlib import Path
import struct
from macho_inspect import MachO

SOURCE_SHA256 = '84cfae57ebe7779a8f43f04f510db86012fbed3f111b2892c4e95572b743df6f'
PARAGRAPH = (b'TablePlus will generate an access token for tableplus-mcp every time the app restarts. '
             b'The token is stored in the app directory so that tableplus-mcp can read it.\n'
             b'If you disable automatic token you must set environment TABLEPLUS_MCP_ACCESS_TOKEN')
STRINGS = (
    (0x100da7820, 0x100e99950, b'/Contents/MacOS/tableplus-mcp', 32),
    (0x100da8be0, 0x100e9ad10, b'Auto-generate Access Token for tableplus-mcp', 48),
    (0x100da8c10, 0x100e9ad40, PARAGRAPH, 256),
    (0x100da8e10, 0x100e9af40, b'Contents/MacOS/tableplus-mcp', 32),
    (0x100da9000, 0x100e9b130, b'tableplus-mcp.pem', 32),
)


def replacement(value):
    return value.replace(b'tableplus-mcp', b'tablecraft-mcp').replace(b'TablePlus will', b'TableCraft will')


def edits():
    result = []
    for arm, intel, value, capacity in STRINGS:
        updated = replacement(value)
        if len(updated) >= capacity:
            raise ValueError('Insufficient original string padding')
        for arch, address in (('arm64', arm), ('x86_64', intel)):
            result.append((arch, address, value.ljust(capacity,b'\0'), updated.ljust(capacity,b'\0')))
    for address, before, after in ((0x10054b874,29,30), (0x100565ad4,28,29),
                                    (0x100576c34,28,29), (0x100577578,28,29), (0x10056c468,17,18)):
        result.append(('arm64',address,struct.pack('<I',0xd2800000|(before<<5)),
                       struct.pack('<I',0xd2800000|(after<<5))))
    for address, dest, source, before, after in ((0x10056b668,0,26,19,20),
            (0x10056b6c4,0,26,220,223), (0x1007710a0,9,23,27,28)):
        base=0x91000000|(source<<5)|dest
        result.append(('arm64',address,struct.pack('<I',base|(before<<10)),struct.pack('<I',base|(after<<10))))
    for address, before, after in ((0x1005dad71,29,30), (0x1005f8a98,28,29),
            (0x10060bc6a,28,29), (0x10060c5f7,28,29), (0x1005fffe9,17,18)):
        result.append(('x86_64',address,b'\x48\xbf'+struct.pack('<Q',0xd000000000000000|before),
                       b'\x48\xbf'+struct.pack('<Q',0xd000000000000000|after)))
    for address, before, after in ((0x1005fef74,'488d7813','488d7814'),
            (0x1005fefe7,'4881c7dc000000','4881c7df000000'), (0x1008462a7,'4883c31b','4883c31c')):
        result.append(('x86_64',address,bytes.fromhex(before),bytes.fromhex(after)))
    for arch, address in (('arm64',0x1011a1938),('x86_64',0x1012e51d0)):
        result.append((arch,address,b'tableplus-mcp\0\0\xed',b'tablecraft-mcp\0\xee'))
    return result


def state(bundle):
    binary=Path(bundle)/'Contents/MacOS/TablePlus'
    slices={arch:MachO(binary,arch) for arch in ('arm64','x86_64')}
    current=[slices[arch].read(address,len(before)) for arch,address,before,_ in edits()]
    if all(actual==after for actual,(_,_,_,after) in zip(current,edits())):return 'TableCraft'
    if all(actual==before for actual,(_,_,before,_) in zip(current,edits())):return 'TablePlus'
    raise ValueError('Incomplete or unsupported MCP settings strings')


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
            raise ValueError('Unexpected MCP settings bytes; nothing written')
        data[offset:offset+len(before)]=after
        changes.append(dict(architecture=arch,address=hex(address),file_offset=offset,before=before.hex(),after=after.hex()))
    binary.write_bytes(data)
    if state(bundle)!='TableCraft':raise ValueError('MCP settings verification failed')
    return changes
