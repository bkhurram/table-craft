"""Remove local tab/workspace count gates from the exact ARM64 830 sample."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import struct

from macho_inspect import MachO

ROOT = Path(__file__).resolve().parent.parent
SOURCE_SHA256 = '8e18e7010a4714e8e8e900db2cb9e82f876438b6936d5d7b9fa2db679d895ef7'
# Each destination is the existing path used when the count is below two.
GATES = (
    (0x1003863d4, 0x100386454, 'workspace creation'),
    (0x1003f0ae4, 0x1003f0b64, 'workspace action A'),
    (0x1003f0ce4, 0x1003f0d64, 'workspace action B'),
    (0x1003f0e94, 0x1003f0f14, 'workspace action C'),
    (0x100594998, 0x100594a18, 'workspace opening'),
    (0x100599344, 0x1005993c4, 'tab creation'),
    (0x100a274f4, 0x100a27574, 'additional workspace operation'),
)
SECONDARY_TAB = (0x10059a67c, 0x10059a754, 'secondary tab marker')
# Presentation-only branches: omit trial notification entries, preserving other notices.
TRIAL_NOTIFICATION_GATES = (
    (0x100018c70, 0x100018d00, 'omit trial notification summary'),
    (0x100019698, 0x1000196f8, 'omit trial notification card'),
)
# Arguments to NSView.setHidden: retain the views/outlets, hide all three controls.
TRIAL_WELCOME_ARGUMENTS = (0x100a2b074, 0x100a2b09c, 0x100a2b0c4)
FILTER_GATES = (
    (0x10073a250, 0x10073a388, 3, 'restore more than two filters'),
    (0x10073b5d0, 0x10073b650, 11, 'create more than two filters'),
    (0x10073b66c, 0x10073b6c8, 11, 'omit secondary filter count warning'),
    (0x10073c0ac, 0x10073c134, 11, 'additional filter creation path'),
)


def validate_source(bundle):
    bundle = Path(bundle)
    info = plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
    if (info.get('CFBundleShortVersionString'), info.get('CFBundleVersion')) != ('27.1.0', '830'):
        raise ValueError('--workspace-limits requires exactly TablePlus 27.1.0 (830)')
    if hashlib.sha256((bundle/'Contents/MacOS/TablePlus').read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported or already modified executable: SHA-256 mismatch')


def patch(bundle, hide_trial_ui=False, filter_limits=False):
    bundle = Path(bundle)
    binary = bundle/'Contents/MacOS/TablePlus'
    if bundle.is_symlink() or binary.is_symlink() or binary.resolve() == Path('/Applications/TablePlus.app/Contents/MacOS/TablePlus').resolve():
        raise ValueError('Only a separate, non-symlink research copy may be modified')
    validate_source(bundle)
    macho = MachO(binary)
    data = bytearray(macho.raw)
    changes = []
    for address, destination, reason in (*GATES, SECONDARY_TAB):
        before = macho.read(address, 4)
        instruction = struct.unpack('<I', before)[0]
        if (address, destination, reason) in GATES:
            # B.LT with this precise destination, not just a matching opcode.
            expected = 0x5400000b | (((destination-address)//4 & 0x7ffff) << 5)
        else:
            expected = 0xb4000008 | (((destination-address)//4 & 0x7ffff) << 5)
        if instruction != expected:
            raise ValueError('Unexpected instruction at {:#x}'.format(address))
        replacement = struct.pack('<I', 0x14000000 | (((destination-address)//4) & 0x3ffffff))
        offset = macho.base + macho.offset(address)
        data[offset:offset+4] = replacement
        changes.append(dict(address_arm64=hex(address), destination=hex(destination),
                            file_offset=offset, before=before.hex(), after=replacement.hex(), reason=reason))
    if hide_trial_ui:
        for address, destination, reason in TRIAL_NOTIFICATION_GATES:
            before = macho.read(address, 4)
            expected = 0x54000000 | (((destination-address)//4 & 0x7ffff) << 5)
            if struct.unpack('<I', before)[0] != expected:
                raise ValueError('Unexpected notification branch at {:#x}'.format(address))
            replacement = struct.pack('<I', 0x14000000 | (((destination-address)//4) & 0x3ffffff))
            offset = macho.base + macho.offset(address)
            data[offset:offset+4] = replacement
            changes.append(dict(address_arm64=hex(address), destination=hex(destination),
                                file_offset=offset, before=before.hex(), after=replacement.hex(), reason=reason))
        for address in TRIAL_WELCOME_ARGUMENTS:
            before = macho.read(address, 4)
            if before != bytes.fromhex('e20313aa'):  # mov x2, x19
                raise ValueError('Unexpected welcome visibility argument at {:#x}'.format(address))
            replacement = bytes.fromhex('22008052')  # mov w2, #1 (hidden)
            offset = macho.base + macho.offset(address)
            data[offset:offset+4] = replacement
            changes.append(dict(address_arm64=hex(address), file_offset=offset, before=before.hex(),
                                after=replacement.hex(), reason='hide welcome trial control'))
    if filter_limits:
        for address, destination, condition, reason in FILTER_GATES:
            before = macho.read(address, 4)
            expected = 0x54000000 | (((destination-address)//4 & 0x7ffff) << 5) | condition
            if struct.unpack('<I', before)[0] != expected:
                raise ValueError('Unexpected filter branch at {:#x}'.format(address))
            replacement = struct.pack('<I', 0x14000000 | (((destination-address)//4) & 0x3ffffff))
            offset = macho.base + macho.offset(address)
            data[offset:offset+4] = replacement
            changes.append(dict(address_arm64=hex(address), destination=hex(destination),
                                file_offset=offset, before=before.hex(), after=replacement.hex(), reason=reason))
    # All guards run before the executable is written.
    binary.write_bytes(data)
    manifest = dict(source_sha256=SOURCE_SHA256, unsigned_patched_sha256=hashlib.sha256(data).hexdigest(),
                    bundle=str(bundle), architecture_modified='arm64', intel_slice_modified=False,
                    scope='local tabs/workspaces' + (' and trial UI visibility' if hide_trial_ui else '')
                    + (' and filter counts' if filter_limits else ''),
                    license_state_modified=False, changes=changes)
    evidence = 'filters-830' if filter_limits else ('trial-ui-830' if hide_trial_ui else 'limits-830')
    output = ROOT/'analysis/evidence'/evidence/'patch-manifest.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2)+'\n')
    print('Applied {} local changes (ARM64); hide trial UI: {}.'.format(len(changes), hide_trial_ui))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hide-trial-ui', action='store_true')
    parser.add_argument('--filter-limits', action='store_true')
    args = parser.parse_args()
    patch(os.environ.get('TABLECRAFT_BUNDLE', ROOT/'analysis/copies/TablePlus-Research.app'),
          args.hide_trial_ui, args.filter_limits)
