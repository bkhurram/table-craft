#!/usr/bin/env python3
"""Rebrand visible NIB strings without renaming Swift modules or user-data domains."""
import json
import os
import plistlib
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = Path(os.environ.get('TABLECRAFT_BUNDLE', ROOT / 'analysis/copies/TablePlus-Research.app'))
RESOURCES = BUNDLE / 'Contents/Resources'
BACKUP = ROOT / 'assets/icons/backup/branding'
SIZES = {0: 1, 1: 2, 2: 4, 3: 8, 6: 4, 7: 8, 10: 4}


def read_var(data, offset):
    value = shift = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        shift += 7
        if byte & 128:
            return value, offset


def var(value):
    result = bytearray()
    while value >= 128:
        result.append(value & 127)
        value >>= 7
    result.append(value | 128)
    return bytes(result)


class Nib:
    def __init__(self, data):
        assert data[:10] == b'NIBArchive'
        self.header = list(struct.unpack_from('<10I', data, 10))
        h = self.header
        self.keys_raw = data[h[5]:h[7]]
        self.classes_raw = data[h[9]:]
        self.keys = []
        p = h[5]
        for _ in range(h[4]):
            n, p = read_var(data, p)
            self.keys.append(data[p:p+n].decode())
            p += n
        assert p == h[7]
        self.objects = []
        p = h[3]
        for _ in range(h[2]):
            cls, p = read_var(data, p)
            start, p = read_var(data, p)
            count, p = read_var(data, p)
            self.objects.append((cls, start, count))
        assert p == h[5]
        self.values = []
        p = h[7]
        for _ in range(h[6]):
            key, p = read_var(data, p)
            kind = data[p]
            p += 1
            if kind == 8:
                n, p = read_var(data, p)
            elif kind in SIZES:
                n = SIZES[kind]
            else:
                assert kind in (4, 5, 9)
                n = 0
            self.values.append([key, kind, data[p:p+n]])
            p += n
        assert p == h[9]

    def encode(self):
        objects = b''.join(var(c)+var(s)+var(n) for c,s,n in self.objects)
        values = b''.join(var(k)+bytes([t])+(var(len(v)) if t == 8 else b'')+v
                          for k,t,v in self.values)
        h = self.header.copy()
        h[2], h[3] = len(self.objects), 50
        h[5] = h[3] + len(objects)
        h[6] = len(self.values)
        h[7] = h[5] + len(self.keys_raw)
        h[9] = h[7] + len(values)
        return b'NIBArchive'+struct.pack('<10I',*h)+objects+self.keys_raw+values+self.classes_raw

    def rebrand(self):
        # A single interned string can serve both a visible label and IBModuleName.
        # Duplicate string objects and redirect only visual/localization references.
        visual_keys = {'NSContents','NSTitle','NSWindowTitle','NSDev','NSResourceName'}
        replacements = {b'TablePlus':b'TableCraft', b'About TablePlus':b'About TableCraft',
                        b'Hide TablePlus':b'Hide TableCraft', b'Quit TablePlus':b'Quit TableCraft',
                        b'elephant':b'CraftElephant'}
        changes = []
        originals = list(enumerate(self.objects))
        for obj_id, (cls, start, count) in originals:
            fields = self.values[start:start+count]
            names = {self.keys[k] for k,t,v in fields}
            if {'NSKey','NSDev','NS.bytes'} <= names:
                for value in fields:
                    if self.keys[value[0]] == 'NS.bytes' and value[1] == 8 and value[2] in replacements:
                        before = value[2]
                        value[2] = replacements[before]
                        changes.append({'from':before.decode(),'to':value[2].decode(),
                                        'localized_string_object':obj_id})
        for obj_id, (cls, start, count) in originals:
            if count != 1:
                continue
            key, kind, data = self.values[start]
            if kind != 8 or self.keys[key] != 'NS.bytes' or data not in replacements:
                continue
            refs = [v for v in self.values if v[1] == 10
                    and self.keys[v[0]] in visual_keys
                    and int.from_bytes(v[2],'little') == obj_id]
            if not refs:
                continue
            new_obj = len(self.objects)
            self.objects.append((cls,len(self.values),1))
            self.values.append([key,kind,replacements[data]])
            for value in refs:
                value[2] = new_obj.to_bytes(4,'little')
            changes.append({'from':data.decode(),'to':replacements[data].decode(),'references':len(refs)})
        return changes


def backup(path):
    dest = BACKUP / path.relative_to(BUNDLE)
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,dest)


def main():
    changes = {}
    for relative in ['Base.lproj/Welcome.nib','AboutWindow.nib']:
        path = RESOURCES / relative
        source = path.read_bytes()
        nib = Nib(source)
        assert nib.encode() == source, 'Original NIB must round-trip byte for byte'
        changes[relative] = nib.rebrand()
        backup(path)
        encoded = nib.encode()
        assert Nib(encoded).encode() == encoded
        path.write_bytes(encoded)
    for path in RESOURCES.glob('*.lproj/Welcome.strings'):
        # Apple .strings input uses the OpenStep plist grammar; convert via plutil.
        import subprocess
        raw = subprocess.check_output(['plutil','-convert','xml1','-o','-',str(path)])
        entries = plistlib.loads(raw)
        updated = {k:(v.replace('TablePlus','TableCraft') if k.endswith('.title') else v)
                   for k,v in entries.items()}
        if updated != entries:
            backup(path)
            path.write_bytes(plistlib.dumps(updated))
            changes[str(path.relative_to(RESOURCES))] = sum(updated[k] != entries[k] for k in entries)
    for path in RESOURCES.glob('*.lproj/Localizable.strings'):
        import subprocess
        entries = plistlib.loads(subprocess.check_output(['plutil','-convert','xml1','-o','-',str(path)]))
        if entries.get('TablePlus') != 'TableCraft':
            backup(path)
            entries['TablePlus'] = 'TableCraft'
            path.write_bytes(plistlib.dumps(entries))
            changes[str(path.relative_to(RESOURCES))] = {'TablePlus':'TableCraft'}
    shutil.copy2(ROOT/'assets/icons/elephant-craft.png', RESOURCES/'CraftElephant.png')
    info_path = BUNDLE/'Contents/Info.plist'
    backup(info_path)
    info = plistlib.loads(info_path.read_bytes())
    info['CFBundleName'] = info['CFBundleDisplayName'] = 'TableCraft'
    info_path.write_bytes(plistlib.dumps(info))
    (ROOT/'assets/icons/branding-manifest.json').write_text(json.dumps(changes,indent=2))
    print(json.dumps(changes,indent=2))


if __name__ == '__main__':
    main()
