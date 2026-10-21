"""Isolate build 830 MCP discovery, token Keychain service and default port.

No credentials are read. All executable anchors and hashes must match before
any staged file is written. The existing app bundle identifier is retained.
"""
import hashlib
from pathlib import Path
import plistlib
from macho_inspect import MachO

BUNDLE_ID = 'com.tinyapp.TablePlus.Research'
TOKEN_SERVICE = 'com.tablecraft.mcp.tokens'
DEFAULT_PORT = 51013
SOURCE_SHA256 = {'TablePlus': 'dff4c0299deafacc13d99213069c048a91bd01347b36657a41c064019d7f0146', 'tablecraft-mcp': 'a210a1b2ba3516235d66f23b751853236fc55b8730b06967eb17464004468395'}
EDITS = (
    ('TablePlus', 'arm64', 0x100da8d80, '636f6d2e7461626c65706c75732e6d63702e746f6b656e730000000000000000', '636f6d2e7461626c6563726166742e6d63702e746f6b656e7300000000000000'),
    ('TablePlus', 'x86_64', 0x100e9aeb0, '636f6d2e7461626c65706c75732e6d63702e746f6b656e730000000000000000', '636f6d2e7461626c6563726166742e6d63702e746f6b656e7300000000000000'),
    ('TablePlus', 'arm64', 0x100565400, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x100566208, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x100566ff0, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x100567840, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x100883c34, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x1008ada84, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x1008adbcc, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x1008b0954, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x1008b0ccc, '020380d2', '220380d2'),
    ('TablePlus', 'arm64', 0x100a4a1f8, '020380d2', '220380d2'),
    ('TablePlus', 'x86_64', 0x1005f831d, '48ba18000000000000d0', '48ba19000000000000d0'),
    ('TablePlus', 'x86_64', 0x1005f927d, '48ba18000000000000d0', '48ba19000000000000d0'),
    ('TablePlus', 'x86_64', 0x1005fa211, '48ba18000000000000d0', '48ba19000000000000d0'),
    ('TablePlus', 'x86_64', 0x1005faac1, '48ba18000000000000d0', '48ba19000000000000d0'),
    ('TablePlus', 'x86_64', 0x100979aa2, '48ba18000000000000d0', '48ba19000000000000d0'),
    ('TablePlus', 'x86_64', 0x1009a8954, '48ba18000000000000d0', '48ba19000000000000d0'),
    ('TablePlus', 'x86_64', 0x1009a8ac3, '48ba18000000000000d0', '48ba19000000000000d0'),
    ('TablePlus', 'x86_64', 0x1009aba1f, '49be18000000000000d0', '49be19000000000000d0'),
    ('TablePlus', 'x86_64', 0x1009abf5e, '49be18000000000000d0', '49be19000000000000d0'),
    ('TablePlus', 'x86_64', 0x100b834f9, '48ba18000000000000d0', '48ba19000000000000d0'),
    ('TablePlus', 'arm64', 0x10000bfdc, '60e79852', 'a0e89852'),
    ('TablePlus', 'arm64', 0x1004d1984, '68e79852', 'a8e89852'),
    ('TablePlus', 'arm64', 0x1004d5308, '68e79852', 'a8e89852'),
    ('TablePlus', 'arm64', 0x1004d531c, '69e79852', 'a9e89852'),
    ('TablePlus', 'arm64', 0x1005643e0, '74e79852', 'b4e89852'),
    ('TablePlus', 'arm64', 0x10056a768, '68e79852', 'a8e89852'),
    ('TablePlus', 'arm64', 0x100879e2c, '6ae79852', 'aae89852'),
    ('TablePlus', 'x86_64', 0x10000cc54, 'b83bc70000', 'b845c70000'),
    ('TablePlus', 'x86_64', 0x100551bca, '49c785580300003bc70000', '49c7855803000045c70000'),
    ('TablePlus', 'x86_64', 0x100555b26, 'b83bc70000', 'b845c70000'),
    ('TablePlus', 'x86_64', 0x100555b39, 'b93bc70000', 'b945c70000'),
    ('TablePlus', 'x86_64', 0x1005f7185, '41be3bc70000', '41be45c70000'),
    ('TablePlus', 'x86_64', 0x1005fdd1f, '48c78540ffffff3bc70000', '48c78540ffffff45c70000'),
    ('TablePlus', 'x86_64', 0x10096eaca, 'b83bc70000', 'b845c70000'),
    ('TablePlus', 'x86_64', 0x1009b1100, 'bb3bc70000', 'bb45c70000'),
    ('TablePlus', 'x86_64', 0x1009b77cd, 'bb3bc70000', 'bb45c70000'),
    ('TablePlus', 'x86_64', 0x100b5e230, '41bf3bc70000', '41bf45c70000'),
    ('tablecraft-mcp', 'arm64', 0x10002b4d0, '636f6d2e74696e796170702e5461626c65506c75730000000000000000000000', '636f6d2e74696e796170702e5461626c65506c75732e52657365617263680000'),
    ('tablecraft-mcp', 'arm64', 0x10002b4f0, '636f6d2e74696e796170702e5461626c65506c75732d73657461707000000000', '636f6d2e74696e796170702e5461626c65506c75732e52657365617263680000'),
    ('tablecraft-mcp', 'arm64', 0x100039168, '15000000000000d0', '1e000000000000d0'),
    ('tablecraft-mcp', 'arm64', 0x100039178, '1c000000000000d0', '1e000000000000d0'),
    ('tablecraft-mcp', 'arm64', 0x10002b3d0, '7461626c65706c75733a2f2f696e746567726174696f6e732f73746172742d6d63700000000000000000000000000000', '7461626c6563726166743a2f2f696e746567726174696f6e732f73746172742d6d637000000000000000000000000000'),
    ('tablecraft-mcp', 'x86_64', 0x10002fbe0, '636f6d2e74696e796170702e5461626c65506c75730000000000000000000000', '636f6d2e74696e796170702e5461626c65506c75732e52657365617263680000'),
    ('tablecraft-mcp', 'x86_64', 0x10002fc00, '636f6d2e74696e796170702e5461626c65506c75732d73657461707000000000', '636f6d2e74696e796170702e5461626c65506c75732e52657365617263680000'),
    ('tablecraft-mcp', 'x86_64', 0x10003af00, '15000000000000d0', '1e000000000000d0'),
    ('tablecraft-mcp', 'x86_64', 0x10003af10, '1c000000000000d0', '1e000000000000d0'),
    ('tablecraft-mcp', 'x86_64', 0x10002fae0, '7461626c65706c75733a2f2f696e746567726174696f6e732f73746172742d6d63700000000000000000000000000000', '7461626c6563726166743a2f2f696e746567726174696f6e732f73746172742d6d637000000000000000000000000000'),
    ('tablecraft-mcp', 'arm64', 0x1000051ec, '899700d1', '899300d1'),
    ('tablecraft-mcp', 'x86_64', 0x100005e0b, '4883c0db', '4883c0dc'),
)


def edits():
    return [(name, arch, address, bytes.fromhex(before), bytes.fromhex(after))
            for name, arch, address, before, after in EDITS]


def state(bundle):
    bundle = Path(bundle)
    slices = {(name, arch): MachO(bundle/'Contents/MacOS'/name, arch)
              for name, arch in {(n, a) for n, a, _, _, _ in edits()}}
    actual = [slices[name, arch].read(address, len(before))
              for name, arch, address, before, _ in edits()]
    info = plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
    schemes = [s for entry in info.get('CFBundleURLTypes', [])
               for s in entry.get('CFBundleURLSchemes', [])]
    if all(a == after for a, (_, _, _, _, after) in zip(actual, edits())) and 'tablecraft' in schemes and 'tableplus' not in schemes:
        return 'isolated'
    if all(a == before for a, (_, _, _, before, _) in zip(actual, edits())) and 'tableplus' in schemes and 'tablecraft' not in schemes:
        return 'shared'
    raise ValueError('Incomplete or unsupported MCP isolation')


def patch(bundle):
    bundle = Path(bundle)
    if bundle.is_symlink() or bundle.resolve() == Path('/Applications/TablePlus.app').resolve():
        raise ValueError('Only a separate non-symlink copy may be modified')
    if state(bundle) == 'isolated':
        return []
    info_path = bundle/'Contents/Info.plist'
    if info_path.is_symlink():
        raise ValueError('Unexpected Info.plist symlink')
    info = plistlib.loads(info_path.read_bytes())
    if info.get('CFBundleIdentifier') != BUNDLE_ID:
        raise ValueError('Unexpected TableCraft bundle identity')
    payloads = {}
    slices = {}
    for name, expected in SOURCE_SHA256.items():
        path = bundle/'Contents/MacOS'/name
        if path.is_symlink():
            raise ValueError('Unexpected executable symlink')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Unsupported executable SHA-256: '+name)
        payloads[name] = bytearray(raw)
        for arch in ('arm64', 'x86_64'):
            slices[name, arch] = MachO(path, arch)
    changes = []
    for name, arch, address, before, after in edits():
        macho = slices[name, arch]
        offset = macho.base+macho.offset(address)
        data = payloads[name]
        if len(before) != len(after) or data[offset:offset+len(before)] != before:
            raise ValueError('Unexpected MCP isolation bytes; nothing written')
        data[offset:offset+len(before)] = after
        changes.append(dict(binary=name, architecture=arch, address=hex(address),
                            before=before.hex(), after=after.hex()))
    for entry in info['CFBundleURLTypes']:
        if 'tableplus' in entry.get('CFBundleURLSchemes', []):
            entry['CFBundleURLSchemes'] = ['tablecraft' if s == 'tableplus' else s for s in entry['CFBundleURLSchemes']]
            entry['CFBundleURLName'] = 'TableCraft'
    for name, data in payloads.items():
        (bundle/'Contents/MacOS'/name).write_bytes(data)
    info_path.write_bytes(plistlib.dumps(info))
    if state(bundle) != 'isolated':
        raise ValueError('MCP isolation verification failed')
    return changes
