"""Locate embedded feature messages and their ARM64 code references."""
import json
import re
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from macho_inspect import MachO

app = MachO('/Applications/TablePlus.app/Contents/MacOS/TablePlus')
out = Path('analysis/evidence/feature-controls')
out.mkdir(parents=True, exist_ok=True)
messages = [b'Free Trial limited 2 workspaces', b'Free Trial limited 2 tabs',
            b'Free Trial limited 2 filters', b'Free Trial limited 1 Metrics Board',
            b'Premium required', b'Your license has expired',
            b"You're using the trial version of TablePlus"]
targets = {}
for message in messages:
    offset = app.data.find(message)
    if offset < 0:
        continue
    for _, va, _, fo, fs in app.segments:
        if fo <= offset < fo+fs:
            addr = va+offset-fo
            for delta in (0, -32):
                targets[addr+delta] = {'message': message.decode(), 'address': hex(addr)}
            break
addr, length, offset = app.sections['__TEXT', '__text']
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.skipdata = True
pages = {}
hits = []
for pc, size, mnemonic, op in md.disasm_lite(app.data[offset:offset+length], addr):
    if mnemonic == 'adrp':
        reg, immediate = op.split(', ')
        pages[reg] = (int(immediate[1:], 0), pc)
    elif mnemonic == 'add':
        m = re.fullmatch(r'(x\d+), (x\d+), #(0x[0-9a-f]+|\d+)', op)
        if m and m[2] in pages:
            page, origin = pages[m[2]]
            target = page+int(m[3], 0)
            if pc-origin <= 64 and target in targets:
                start, end = app.function(pc)
                hits.append(dict(targets[target], pc=hex(pc), function=hex(start), end=hex(end)))
    elif mnemonic == 'adr':
        m = re.fullmatch(r'x\d+, #(0x[0-9a-f]+)', op)
        if m and int(m[1],0) in targets:
            start,end=app.function(pc)
            hits.append(dict(targets[int(m[1],0)], pc=hex(pc), function=hex(start), end=hex(end)))

for start, end in sorted({(int(x['function'],0), int(x['end'],0)) for x in hits}):
    lines = [f'{pc:#x}: {mnemonic:8} {op}' for pc, _, mnemonic, op in md.disasm_lite(app.read(start,end-start), start)]
    (out / f'{start:x}.asm').write_text('\n'.join(lines)+'\n')
(out / 'message-xrefs.json').write_text(json.dumps(hits,indent=2))
print(json.dumps(hits,indent=2))
