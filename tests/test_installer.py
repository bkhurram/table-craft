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
        tools = self.root / 'tools'
        tools.mkdir()
        self.env['PATH'] = str(tools) + os.pathsep + self.env['PATH']
        self.executable(tools/'uname', '#!/bin/zsh\n[[ $1 == -s ]] && print Darwin || print arm64\n')
        self.executable(tools/'codesign', '#!/bin/zsh\nexit 0\n')
        self.executable(tools/'ditto', '#!{}\nimport shutil, sys\nshutil.copytree(sys.argv[1], sys.argv[2])\n'.format(sys.executable))
        shutil.copy2(ROOT/'scripts/python_runtime.sh', scripts/'python_runtime.sh')
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
