"""Apply version-pinned ARM64 changes only to the separate research bundle."""
import hashlib
import json
import os
import plistlib
import struct
from pathlib import Path
from macho_inspect import MachO

ROOT = Path(__file__).resolve().parent.parent
bundle = Path(os.environ.get('TABLECRAFT_BUNDLE', ROOT / 'analysis/copies/TablePlus-Research.app'))
binary = bundle / 'Contents/MacOS/TablePlus'
expected = '4547216d88fcd2868e48f31a2079da27850ace793ae79cc0fb7963d9c827c05a'
assert binary.resolve() != Path('/Applications/TablePlus.app/Contents/MacOS/TablePlus').resolve()
assert hashlib.sha256(binary.read_bytes()).hexdigest() == expected, 'Unsupported or already modified binary'
macho = MachO(binary)
data = bytearray(macho.raw)
changes = []


def replace(address, replacement, reason):
    off = macho.base + macho.offset(address)
    before = bytes(data[off:off+len(replacement)])
    data[off:off+len(replacement)] = replacement
    changes.append({'address_arm64': hex(address), 'file_offset': off,
                    'before': before.hex(), 'after': replacement.hex(), 'reason': reason})


def branch(address, destination, reason):
    relative = destination-address
    assert relative % 4 == 0 and -(1 << 27) <= relative < (1 << 27)
    replace(address, struct.pack('<I', 0x14000000 | ((relative >> 2) & 0x3ffffff)), reason)


# Skip complete inline checks before any license object is retained or dereferenced.
gates = [
    (0x10037704c, 0x1003770b0, 'workspace creation'),
    (0x1003d07d8, 0x1003d083c, 'workspace action A'),
    (0x1003d09d8, 0x1003d0a3c, 'workspace action B'),
    (0x1003d0b88, 0x1003d0bec, 'workspace action C'),
    (0x100536ee0, 0x100536f44, 'workspace preferences'),
    (0x100538970, 0x1005389d4, 'workspace opening'),
    (0x10053d31c, 0x10053d380, 'tab creation'),
    (0x1005ad1b8, 0x1005ad258, 'four-item local limit'),
    (0x1006d7468, 0x1006d7584, 'filter restoration'),
    (0x1006d87e8, 0x1006d88c4, 'filter creation'),
    (0x1006d92c4, 0x1006d9330, 'filter operation'),
    (0x10079bf3c, 0x10079bfc4, 'metrics board operation'),
    (0x10079cbe4, 0x10079cc48, 'metrics board creation'),
    (0x1008c0e1c, 0x1008c0d24, 'crash reporting preference'),
    (0x1009a1498, 0x1009a14fc, 'additional workspace operation'),
]
for address, destination, reason in gates:
    instruction = struct.unpack('<I', macho.read(address,4))[0]
    assert instruction & 0x7f000000 == 0x34000000, f'Expected CBZ at {address:#x}'
    branch(address, destination, reason)

# Secondary tab path checks a local trial marker after releasing its temporary values.
assert struct.unpack('<I', macho.read(0x10053e638,4))[0] & 0x7f000000 == 0x34000000
branch(0x10053e638, 0x10053e710, 'secondary tab marker')

# Two UI paths materialize the result into callee-saved boolean registers.
for address, register, destination in [(0x1009954d4,20,0x10099554c), (0x10099a9c4,19,0x10099aa3c)]:
    replace(address, struct.pack('<I', 0x52800020 | register), 'local feature availability boolean')
    branch(address+4,destination,'continue UI availability update')

# Pure license-state presentation helper: the existing success enum value is 2.
replace(0x100024894, bytes.fromhex('40008052c0035fd6'), 'license-state presentation helper')
binary.write_bytes(data)
info_path = bundle / 'Contents/Info.plist'
info = plistlib.loads(info_path.read_bytes())
info['CFBundleIdentifier'] = 'com.tinyapp.TablePlus.Research'
info['CFBundleName'] = 'TablePlus Research'
info['CFBundleDisplayName'] = 'TablePlus Research'
info['SUEnableAutomaticChecks'] = False
info['SUAutomaticallyUpdate'] = False
info['SUAllowsAutomaticUpdates'] = False
info_path.write_bytes(plistlib.dumps(info))
manifest = {'source_sha256': expected, 'unsigned_patched_sha256': hashlib.sha256(data).hexdigest(),
            'bundle': str(bundle), 'architecture_modified': 'arm64',
            'intel_slice_modified': False, 'changes': changes}
manifest_path = ROOT/'analysis/evidence/feature-controls/patch-manifest.json'
manifest_path.parent.mkdir(parents=True, exist_ok=True)
manifest_path.write_text(json.dumps(manifest,indent=2))
print(json.dumps({'bundle':str(bundle),'changes':len(changes),'architecture':'arm64'},indent=2))
