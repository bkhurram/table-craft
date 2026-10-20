"""Guard identity changes, both Swift string lengths and untouched executable bytes."""
import hashlib
from pathlib import Path
import plistlib
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import patch_keychain_identity as keychain


class KeychainIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tablecraft-keychain-test-')
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name)/'Fixture.app'
        (self.bundle/'Contents/MacOS').mkdir(parents=True)
        self.binary = self.bundle/'Contents/MacOS/TablePlus'
        self.info = self.bundle/'Contents/Info.plist'
        self.info.write_bytes(plistlib.dumps({'CFBundleVersion': '830'}))
        mapping = {(arch, address): 64+i*64 for i, (arch, address, _, _) in enumerate(keychain.edits())}
        raw = bytearray(b'X'*2048)
        for arch, address, before, _ in keychain.edits():
            offset = mapping[arch, address]
            raw[offset:offset+len(before)] = before
        self.binary.write_bytes(raw)
        self.original = bytes(raw)
        self.mapping = mapping

        class FixtureMachO:
            def __init__(self, path, arch='arm64'):
                self.path, self.arch, self.base = Path(path), arch, 0
            def offset(self, address):
                return mapping[self.arch, address]
            def read(self, address, size):
                offset = self.offset(address)
                return self.path.read_bytes()[offset:offset+size]

        self.addCleanup(patch.stopall)
        patch.object(keychain, 'MachO', FixtureMachO).start()
        patch.object(keychain, 'SUPPORTED_SHA256', {hashlib.sha256(raw).hexdigest()}).start()

    def test_patch_preserves_every_unrelated_byte_and_is_idempotent(self):
        self.assertEqual(keychain.identity(self.bundle), 'legacy')
        changes = keychain.patch(self.bundle)
        self.assertEqual(keychain.identity(self.bundle), 'isolated')
        expected = bytearray(self.original)
        for arch, address, before, after in keychain.edits():
            offset = self.mapping[arch, address]
            expected[offset:offset+len(before)] = after
        self.assertEqual(self.binary.read_bytes(), expected)
        self.assertEqual(len(changes), 20)
        self.assertEqual(keychain.patch(self.bundle), [])
        self.assertEqual(self.binary.read_bytes(), expected)

    def test_unrecognized_hash_refuses_to_write(self):
        raw = bytearray(self.original); raw[-1] ^= 1
        self.binary.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            keychain.patch(self.bundle)
        self.assertEqual(self.binary.read_bytes(), raw)

    def test_partial_identity_refuses_to_write(self):
        arch, address, _, after = keychain.edits()[0]
        raw = bytearray(self.original); offset=self.mapping[arch, address]
        raw[offset:offset+len(after)] = after
        self.binary.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            keychain.patch(self.bundle)
        self.assertEqual(self.binary.read_bytes(), raw)

    def test_other_build_and_symlink_are_rejected(self):
        self.info.write_bytes(plistlib.dumps({'CFBundleVersion': '818'}))
        with self.assertRaisesRegex(ValueError, '830'):
            keychain.patch(self.bundle)
        link = self.bundle.parent/'linked.app'; link.symlink_to(self.bundle)
        with self.assertRaisesRegex(ValueError, 'non-symlink'):
            keychain.patch(link)
        self.assertEqual(self.binary.read_bytes(), self.original)

    def test_semantic_strings_and_swift_lengths_match_requested_names(self):
        self.assertEqual(len(keychain.SERVICE), 25)
        self.assertEqual(keychain.SERVICE, 'com.tablecraft.TableCraft')
        all_edits = keychain.edits()
        for arch, _, _, after in all_edits[:2]:
            self.assertEqual(after.split(b'\0')[0], keychain.SERVICE.encode())
        for arch, address, before, after in all_edits:
            if arch == 'arm64' and len(after) == 4 and before == keychain.mov_wide(9, 23):
                self.assertEqual((struct.unpack('<I', after)[0] >> 5) & 0xffff, 25)
            if arch == 'x86_64' and before.endswith(struct.pack('<Q', 0xd000000000000017)):
                self.assertEqual(int.from_bytes(after[2:], 'little') & 0xffff, 25)
        # Decode both halves of the Intel Swift small string, including its length tag.
        first, second = all_edits[-2][3][2:], all_edits[-1][3][2:]
        self.assertEqual((first+second)[:10], b'TableCraft')
        self.assertEqual(second[-1], 0xea)


if __name__ == '__main__':
    unittest.main()
