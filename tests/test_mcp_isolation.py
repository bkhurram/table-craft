"""Check atomic preflight across app/helper, scheme separation and corruption guards."""
import hashlib
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import patch_mcp_isolation as isolation


class MCPIsolationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='tablecraft-mcp-isolation-')
        self.addCleanup(temp.cleanup)
        self.bundle = Path(temp.name)/'Fixture.app'
        self.bin = self.bundle/'Contents/MacOS'
        self.bin.mkdir(parents=True)
        self.info = self.bundle/'Contents/Info.plist'
        self.info.write_bytes(plistlib.dumps(dict(CFBundleIdentifier=isolation.BUNDLE_ID,
            CFBundleURLTypes=[dict(CFBundleURLName='tableplus', CFBundleURLSchemes=['tableplus']),
                              dict(CFBundleURLName='Postgres', CFBundleURLSchemes=['postgres'])])))
        mapping = {(n, a, addr): 64+i*64 for i, (n, a, addr, _, _) in enumerate(isolation.edits())}
        self.original = {}
        for name in isolation.SOURCE_SHA256:
            raw = bytearray(b'X'*8192)
            for n, arch, addr, before, _ in isolation.edits():
                if n == name:
                    off = mapping[n, arch, addr]
                    raw[off:off+len(before)] = before
            self.original[name] = bytes(raw)
            (self.bin/name).write_bytes(raw)
        class FixtureMachO:
            def __init__(self, path, arch='arm64'):
                self.path, self.arch, self.base = Path(path), arch, 0
            def offset(self, addr):
                return mapping[self.path.name, self.arch, addr]
            def read(self, addr, length):
                off = self.offset(addr)
                return self.path.read_bytes()[off:off+length]
        self.addCleanup(patch.stopall)
        patch.object(isolation, 'MachO', FixtureMachO).start()
        patch.object(isolation, 'SOURCE_SHA256', {n:hashlib.sha256(d).hexdigest() for n,d in self.original.items()}).start()

    def test_namespaces_and_other_url_schemes_are_preserved(self):
        self.assertEqual(isolation.state(self.bundle), 'shared')
        isolation.patch(self.bundle)
        self.assertEqual(isolation.state(self.bundle), 'isolated')
        info = plistlib.loads(self.info.read_bytes())
        self.assertEqual(info['CFBundleURLTypes'][0]['CFBundleURLSchemes'], ['tablecraft'])
        self.assertEqual(info['CFBundleURLTypes'][1]['CFBundleURLSchemes'], ['postgres'])
        self.assertEqual(isolation.patch(self.bundle), [])
        for n,d in self.original.items():
            self.assertEqual(len((self.bin/n).read_bytes()), len(d))

    def test_unknown_helper_hash_leaves_app_and_plist_untouched(self):
        info = self.info.read_bytes()
        helper = self.bin/'tablecraft-mcp'
        corrupted = helper.read_bytes()[:-1]+b'Y'
        helper.write_bytes(corrupted)
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            isolation.patch(self.bundle)
        self.assertEqual((self.bin/'TablePlus').read_bytes(), self.original['TablePlus'])
        self.assertEqual(helper.read_bytes(), corrupted)
        self.assertEqual(self.info.read_bytes(), info)

    def test_partial_update_is_rejected(self):
        name, arch, addr, _, after = isolation.edits()[0]
        off = isolation.MachO(self.bin/name, arch).offset(addr)
        raw = bytearray((self.bin/name).read_bytes())
        raw[off:off+len(after)] = after
        (self.bin/name).write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            isolation.patch(self.bundle)
        self.assertEqual((self.bin/name).read_bytes(), raw)

    def test_wrong_bundle_identity_is_rejected(self):
        info = plistlib.loads(self.info.read_bytes())
        info['CFBundleIdentifier'] = 'com.tinyapp.TablePlus'
        self.info.write_bytes(plistlib.dumps(info))
        with self.assertRaisesRegex(ValueError, 'bundle identity'):
            isolation.patch(self.bundle)
        for n,d in self.original.items():
            self.assertEqual((self.bin/n).read_bytes(), d)


if __name__ == '__main__':
    unittest.main()
