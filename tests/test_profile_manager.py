"""Synthetic connection data only: migration, backup and checkout independence."""
import os
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'scripts'))
from profile_manager import prepare_profile, profile_path, snapshot_profile


class ProfileTests(unittest.TestCase):
    def test_migration_and_update_snapshot_preserve_connections_and_groups(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root/'checkout/analysis/runtime-profile'
            data = legacy/'Library/Application Support/com.tinyapp.TablePlus.Research/Data'
            data.mkdir(parents=True)
            for name in ('Connections', 'ConnectionGroups'):
                (data/(name+'.plist')).write_bytes(plistlib.dumps({'fixture': name}))
            dest = root/'user data/runtime-profile'
            prepare_profile(dest, legacy)
            self.assertTrue(legacy.exists())
            saved = snapshot_profile(dest)
            for source in legacy.rglob('*.plist'):
                relative = source.relative_to(legacy)
                self.assertEqual((dest/relative).read_bytes(), source.read_bytes())
                self.assertEqual((saved/relative).read_bytes(), source.read_bytes())
            shutil_target = root/'different checkout/analysis/runtime-profile'
            prepare_profile(dest, shutil_target)
            self.assertTrue((dest/data.relative_to(legacy)/'Connections.plist').exists())
            self.assertEqual(dest.stat().st_mode & 0o777, 0o700)

    def test_existing_destination_is_never_merged_or_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy, dest = root/'old', root/'new'
            for path, value in ((legacy, 'old'), (dest, 'new')):
                path.mkdir()
                (path/'Connections.plist').write_text(value)
            prepare_profile(dest, legacy)
            self.assertEqual((dest/'Connections.plist').read_text(), 'new')
            self.assertEqual((legacy/'Connections.plist').read_text(), 'old')

    def test_copy_failure_does_not_publish_partial_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy, dest = root/'old', root/'new'
            legacy.mkdir()
            with patch('profile_manager.shutil.copytree', side_effect=OSError('fixture failure')):
                with self.assertRaises(OSError):
                    prepare_profile(dest, legacy)
            self.assertFalse(dest.exists())
            self.assertFalse((root/'.new.migration-lock').exists())
            prepare_profile(dest, legacy)
            self.assertTrue(dest.is_dir())

    def test_override_requires_absolute_path(self):
        with patch.dict(os.environ, {'TABLECRAFT_PROFILE': 'relative'}):
            with self.assertRaises(ValueError):
                profile_path()

    def test_default_profile_is_independent_of_checkout(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(profile_path(), Path.home()/'Library/Application Support/TableCraft/runtime-profile')


if __name__ == '__main__':
    unittest.main()
