"""Ensure a portable snapshot preserves files/links and fails closed on changes."""
import importlib.util
from pathlib import Path
import tempfile
import json
import shutil
import sys
from unittest.mock import patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))

spec = importlib.util.spec_from_file_location('portable_runtime', Path(__file__).resolve().parents[1]/'scripts/portable_runtime.py')
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


class PortableInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tablecraft-portable-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root/'Runtime.app'
        (self.bundle/'Versions/A').mkdir(parents=True)
        (self.bundle/'Versions/A/library').write_bytes(b'framework')
        (self.bundle/'Versions/Current').symlink_to('A')
        (self.bundle/'library').symlink_to('Versions/Current/library')

    def test_relocation_keeps_snapshot_and_internal_framework_links(self):
        before = portable.inventory(self.bundle)
        relocated = self.root/'another location.app'
        self.bundle.rename(relocated)
        self.assertEqual(before, portable.inventory(relocated))
        self.assertEqual((relocated/'library').read_bytes(), b'framework')

    def test_files_additions_removals_permissions_and_link_changes_are_detected(self):
        before = portable.inventory(self.bundle)
        file = self.bundle/'Versions/A/library'
        file.write_bytes(b'changed')
        self.assertNotEqual(before, portable.inventory(self.bundle))
        file.write_bytes(b'framework')
        file.chmod(0o700)
        self.assertNotEqual(before, portable.inventory(self.bundle))
        file.chmod(before['Versions/A/library']['mode'])
        self.assertEqual(before, portable.inventory(self.bundle))
        extra = self.bundle/'extra'
        extra.touch()
        self.assertNotEqual(before, portable.inventory(self.bundle))
        extra.unlink()
        file.unlink()
        self.assertNotEqual(before, portable.inventory(self.bundle))

    def test_external_symlink_is_rejected(self):
        for target in ('/usr/lib', '../outside'):
            link = self.bundle/'external'
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'External runtime symlink'):
                portable.inventory(self.bundle)
            link.unlink()

    def test_top_level_symlink_is_rejected(self):
        link = self.root/'linked.app'
        link.symlink_to(self.bundle)
        with self.assertRaisesRegex(ValueError, 'real application directory'):
            portable.inventory(link)


class RuntimeUpgradeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tablecraft-upgrade-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root/'runtime'
        self.bundle = self.runtime/'TableCraft.app'
        self.bundle.mkdir(parents=True)
        (self.bundle/'keep').write_text('original application')
        (self.runtime/'manifest.json').write_text('{}')
        self.addCleanup(patch.stopall)
        patch.object(portable, 'ROOT', self.root).start()
        patch.object(portable, 'verify', return_value=self.bundle).start()
        patch.object(portable, 'inventory', return_value={}).start()
        patch.object(portable, 'overrides', return_value={'keychain_identity': True}).start()
        patch('patch_keychain_identity.identity', return_value='legacy').start()
        patch('patch_keychain_identity.patch', return_value=[]).start()

    @staticmethod
    def copy_or_sign(command, **kwargs):
        if command[0] == '/usr/bin/ditto':
            shutil.copytree(command[1], command[2], symlinks=True)

    def assert_original(self):
        self.assertEqual((self.bundle/'keep').read_text(), 'original application')
        self.assertEqual((self.runtime/'manifest.json').read_text(), '{}')
        self.assertEqual(list(self.root.glob('.tablecraft-keychain-*')), [])

    def test_signing_failure_preserves_original_and_cleans_stage(self):
        def fail_signing(command, **kwargs):
            if command[0] == '/usr/bin/codesign':
                raise OSError('synthetic signing failure')
            self.copy_or_sign(command, **kwargs)
        with patch.object(portable.subprocess, 'run', side_effect=fail_signing):
            with self.assertRaisesRegex(OSError, 'signing failure'):
                portable.isolate_keychain(self.runtime)
        self.assert_original()

    def test_publication_failure_restores_original_runtime(self):
        original_rename = Path.rename
        def fail_publication(path, destination):
            if path.parent.name.startswith('.tablecraft-keychain-'):
                raise OSError('synthetic publication failure')
            return original_rename(path, destination)
        with patch.object(portable.subprocess, 'run', side_effect=self.copy_or_sign), \
                patch.object(Path, 'rename', fail_publication):
            with self.assertRaisesRegex(OSError, 'publication failure'):
                portable.isolate_keychain(self.runtime)
        self.assert_original()


if __name__ == '__main__':
    unittest.main()
