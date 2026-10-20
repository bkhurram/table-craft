"""Exercise installer recovery with a small synthetic application and fake macOS tools."""
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'scripts'))
from rebrand_tablecraft import Nib, var
SOURCE_HASH = '4547216d88fcd2868e48f31a2079da27850ace793ae79cc0fb7963d9c827c05a'


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tablecraft-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'download with spaces'
        scripts = self.root / 'scripts'
        scripts.mkdir(parents=True)
        self.env = os.environ.copy()
        for key in ('TABLECRAFT_BUNDLE', 'TABLECRAFT_PYTHON'):
            self.env.pop(key, None)
        self.env['TABLECRAFT_PYTHON'] = sys.executable
        self.env['TABLECRAFT_PROFILE'] = str(self.root/'stable user data/runtime-profile')
        tools = self.root / 'tools'
        tools.mkdir()
        self.env['PATH'] = str(tools) + os.pathsep + self.env['PATH']
        self.executable(tools/'uname', '#!/bin/zsh\n[[ $1 == -s ]] && print Darwin || print arm64\n')
        self.executable(tools/'pgrep', '#!/bin/zsh\nexit ${TABLECRAFT_TEST_PROCESS_STATUS:-1}\n')
        self.executable(tools/'codesign', '#!/bin/zsh\nexit 0\n')
        self.executable(tools/'ditto', '#!{}\nimport shutil, sys\nshutil.copytree(sys.argv[1], sys.argv[2])\n'.format(sys.executable))
        shutil.copy2(ROOT/'scripts/python_runtime.sh', scripts/'python_runtime.sh')
        shutil.copy2(ROOT/'scripts/profile_manager.py', scripts/'profile_manager.py')
        shutil.copy2(ROOT/'scripts/patch_workspace_limits.py', scripts/'patch_workspace_limits.py')
        shutil.copy2(ROOT/'scripts/macho_inspect.py', scripts/'macho_inspect.py')
        self.source = self.root / 'Source App.app'
        (self.source/'Contents/MacOS').mkdir(parents=True)
        self.binary = self.source/'Contents/MacOS/TablePlus'
        self.executable(self.binary, '#!/bin/zsh\nexit 0\n')
        self.digest = hashlib.sha256(self.binary.read_bytes()).hexdigest()
        (self.source/'Contents/Info.plist').write_bytes(plistlib.dumps({
            'CFBundleShortVersionString': '27.0.2', 'CFBundleVersion': '818',
            'CFBundleName': 'TablePlus', 'CFBundleIdentifier': 'com.tinyapp.TablePlus',
            'CFBundleExecutable': 'TablePlus',
        }))
        resources = self.source/'Contents/Resources'
        (resources/'Base.lproj').mkdir(parents=True)
        # Synthetic archive exercising the localized-string path; no vendor data.
        nib = object.__new__(Nib)
        nib.header = [1, 0, 0, 0, 3, 0, 0, 0, 0, 0]
        nib.keys_raw = b''.join(var(len(k)) + k for k in (b'NSKey', b'NSDev', b'NS.bytes'))
        nib.classes_raw = b''
        nib.objects = [(0, 0, 3)]
        nib.values = [(0, 8, b'label'), (1, 8, b''), (2, 8, b'TablePlus')]
        for relative in ('Base.lproj/Welcome.nib', 'AboutWindow.nib'):
            (resources/relative).write_bytes(nib.encode())
        (resources/'AppIcon.icns').write_bytes(b'fixture')
        # Pin the test copy to the fixture, leaving the shipped verifier unchanged.
        (scripts/'setup_tablecraft.sh').write_text(
            (ROOT/'scripts/setup_tablecraft.sh').read_text().replace(SOURCE_HASH, self.digest))
        assets = self.root/'assets/icons'
        assets.mkdir(parents=True)
        for name in ('elephant-craft.png', 'ElephantCraft.icns'):
            (assets/name).write_bytes(b'fixture')
        shutil.copy2(ROOT/'scripts/rebrand_tablecraft.py', scripts/'rebrand_tablecraft.py')
        (scripts/'install_craft_icon.sh').write_text(
            '#!/bin/zsh\n[[ ${TABLECRAFT_TEST_FAIL:-0} != 1 ]] || exit 42\n'
            'touch "$TABLECRAFT_BUNDLE/signed-fixture"\n')
        (scripts/'write_sandbox_profile.py').write_text('pass\n')

    @staticmethod
    def executable(path, content):
        path.write_text(content)
        path.chmod(0o755)

    def run_setup(self, *args):
        return subprocess.run(['/bin/zsh', str(self.root/'scripts/setup_tablecraft.sh'),
                               '--source', str(self.source), *args], env=self.env,
                              text=True, capture_output=True)

    def test_check_only_does_not_create_copy(self):
        result = self.run_setup('--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root/'analysis').exists())

    def test_workspace_limits_reject_wrong_version_before_copy(self):
        result = self.run_setup('--check', '--workspace-limits')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires exactly TablePlus 27.1.0 (830)', result.stderr)
        self.assertFalse((self.root/'analysis').exists())

    def test_workspace_limits_reject_wrong_hash_before_update(self):
        self.assertEqual(self.run_setup().returncode, 0)
        target = self.root/'analysis/copies/TablePlus-Research.app/Contents/MacOS/TablePlus'
        before = target.read_bytes()
        info_path = self.source/'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info.update(CFBundleShortVersionString='27.1.0', CFBundleVersion='830')
        info_path.write_bytes(plistlib.dumps(info))
        result = self.run_setup('--update', '--workspace-limits')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SHA-256 mismatch', result.stderr)
        self.assertEqual(target.read_bytes(), before)
        self.assertFalse((self.root/'stable user data').exists())

    def test_mutually_exclusive_patch_modes(self):
        result = self.run_setup('--workspace-limits', '--local-controls')
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root/'analysis').exists())

    def test_hide_trial_ui_keeps_workspace_version_guard(self):
        result = self.run_setup('--hide-trial-ui', '--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires exactly TablePlus 27.1.0 (830)', result.stderr)
        self.assertFalse((self.root/'analysis').exists())

    def test_filter_limits_keep_version_guard_before_update(self):
        result = self.run_setup('--filter-limits', '--hide-trial-ui', '--update', '--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires exactly TablePlus 27.1.0 (830)', result.stderr)
        self.assertFalse((self.root/'analysis').exists())

    def test_failure_cleans_staging_and_allows_retry_without_touching_profile(self):
        profile = self.root/'analysis/runtime-profile/keep.txt'
        profile.parent.mkdir(parents=True)
        profile.write_text('existing profile')
        self.env['TABLECRAFT_TEST_FAIL'] = '1'
        failed = self.run_setup()
        self.assertEqual(failed.returncode, 42, failed.stderr)
        copies = self.root/'analysis/copies'
        self.assertEqual(list(copies.iterdir()), [])
        self.assertEqual(profile.read_text(), 'existing profile')
        self.env.pop('TABLECRAFT_TEST_FAIL')
        retry = self.run_setup()
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertTrue((copies/'TablePlus-Research.app/signed-fixture').exists())
        self.assertFalse((copies/'.setup-lock').exists())
        self.assertEqual(hashlib.sha256(self.binary.read_bytes()).hexdigest(), self.digest)
        self.assertEqual(profile.read_text(), 'existing profile')

    def test_existing_copy_is_preserved(self):
        bundle = self.root/'analysis/copies/TablePlus-Research.app'
        bundle.mkdir(parents=True)
        (bundle/'keep.txt').write_text('keep')
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('will not overwrite', result.stderr)
        self.assertEqual((bundle/'keep.txt').read_text(), 'keep')

    def test_invalid_explicit_python_reports_requirement(self):
        self.env['TABLECRAFT_PYTHON'] = str(self.root/'missing-python')
        result = self.run_setup('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Python 3.9 or later was not found', result.stderr)

    def test_hash_mismatch_stops_before_copying(self):
        self.binary.write_text('changed source')
        result = self.run_setup('--local-controls')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('hash does not match', result.stderr)
        self.assertFalse((self.root/'analysis').exists())

    def test_802_branding_uses_resource_checks_without_818_hash(self):
        info_path = self.source/'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info.update(CFBundleShortVersionString='26.10.22', CFBundleVersion='802')
        info_path.write_bytes(plistlib.dumps(info))
        self.binary.write_text('different source build')
        source_bytes = self.binary.read_bytes()
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('26.10.22 (802)', result.stdout)
        bundle = self.root/'analysis/copies/TablePlus-Research.app'
        output = plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
        self.assertEqual(output['CFBundleName'], 'TableCraft')
        self.assertEqual((bundle/'Contents/MacOS/TablePlus').read_bytes(), source_bytes)
        self.assertEqual(self.binary.read_bytes(), source_bytes)
        self.assertEqual(info_path.read_bytes(), plistlib.dumps(info))
        rejected = self.run_setup('--check', '--local-controls')
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('--local-controls requires exactly 27.0.2 (818)', rejected.stderr)

    def use_830(self):
        info_path = self.source/'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info.update(CFBundleShortVersionString='27.1.0', CFBundleVersion='830')
        info_path.write_bytes(plistlib.dumps(info))
        (self.source/'Contents/Resources/AboutWindow.nib').unlink()

    def test_830_without_about_window_installs_with_unchanged_executable(self):
        self.use_830()
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root/'analysis/copies/TablePlus-Research.app'
        self.assertEqual((output/'Contents/MacOS/TablePlus').read_bytes(), self.binary.read_bytes())

    def test_update_between_both_versions_preserves_connections_and_previous_bundle(self):
        self.assertEqual(self.run_setup().returncode, 0)
        legacy = self.root/'analysis/runtime-profile/Connections.plist'
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(plistlib.dumps({'fixture': ['connection']}))
        self.use_830()
        result = self.run_setup('--update')
        self.assertEqual(result.returncode, 0, result.stderr)
        copies = self.root/'analysis/copies'
        self.assertEqual(len(list(copies.glob('previous.*/TablePlus-Research.app'))), 1)
        stable = Path(self.env['TABLECRAFT_PROFILE'])
        self.assertEqual((stable/'Connections.plist').read_bytes(), legacy.read_bytes())
        self.assertEqual(len(list(stable.parent.glob('profile-backups/*/runtime-profile/Connections.plist'))), 1)
        # Downgrade packaging remains supported; vendor data format rollback is separate.
        info_path = self.source/'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info.update(CFBundleShortVersionString='27.0.2', CFBundleVersion='818')
        info_path.write_bytes(plistlib.dumps(info))
        shutil.copy2(self.source/'Contents/Resources/Base.lproj/Welcome.nib',
                     self.source/'Contents/Resources/AboutWindow.nib')
        self.assertEqual(self.run_setup('--update').returncode, 0)
        self.assertEqual((stable/'Connections.plist').read_bytes(), legacy.read_bytes())

    def test_failed_update_preserves_previous_application_and_profile(self):
        self.assertEqual(self.run_setup().returncode, 0)
        self.use_830()
        self.env['TABLECRAFT_TEST_FAIL'] = '1'
        failed = self.run_setup('--update')
        self.assertEqual(failed.returncode, 42, failed.stderr)
        old = self.root/'analysis/copies/TablePlus-Research.app/Contents/Info.plist'
        self.assertEqual(plistlib.loads(old.read_bytes())['CFBundleVersion'], '818')
        self.assertFalse((old.parents[2]/'.setup-lock').exists())

    def test_swap_failure_restores_previous_bundle(self):
        self.assertEqual(self.run_setup().returncode, 0)
        self.use_830()
        self.executable(self.root/'tools/mv', '#!/bin/zsh\n'
                        '[[ $1 != *".tablecraft-setup."* ]] || exit 44\n'
                        'exec /bin/mv "$@"\n')
        failed = self.run_setup('--update')
        self.assertEqual(failed.returncode, 44, failed.stderr)
        old = self.root/'analysis/copies/TablePlus-Research.app/Contents/Info.plist'
        self.assertEqual(plistlib.loads(old.read_bytes())['CFBundleVersion'], '818')
        self.assertFalse((self.root/'analysis/copies/.setup-lock').exists())

    def test_update_check_does_not_create_profile_or_copy(self):
        self.use_830()
        result = self.run_setup('--update', '--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(Path(self.env['TABLECRAFT_PROFILE']).exists())
        self.assertFalse((self.root/'analysis').exists())

    def test_update_does_not_migrate_license_control_patches(self):
        result = self.run_setup('--update', '--local-controls')
        self.assertEqual(result.returncode, 2)
        self.assertIn('--update supports branding only', result.stderr)
        self.assertFalse((self.root/'analysis').exists())

    def test_running_app_or_process_inspection_error_blocks_update(self):
        for status in ('0', '2'):
            self.env['TABLECRAFT_TEST_PROCESS_STATUS'] = status
            result = self.run_setup('--update')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Close TablePlus/TableCraft', result.stderr)
            self.assertFalse((self.root/'analysis/copies/.setup-lock').exists())

    def test_incompatible_branding_resources_stop_before_copying(self):
        (self.source/'Contents/Resources/AboutWindow.nib').write_bytes(b'unsupported format')
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unsupported branding resources', result.stderr)
        self.assertFalse((self.root/'analysis').exists())

    def test_missing_asset_reports_incomplete_download(self):
        (self.root/'assets/icons/ElephantCraft.icns').unlink()
        result = self.run_setup('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Download the complete repository ZIP again', result.stderr)


if __name__ == '__main__':
    unittest.main()
