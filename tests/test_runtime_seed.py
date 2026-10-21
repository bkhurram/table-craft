"""Clean-checkout restore integrity, failure recovery and archive boundaries."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import runtime_seed as seed


class RuntimeSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'runtime-seed'
        self.source.mkdir()
        self.destination = self.root/'runtime'
        archive = self.root/'runtime.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('runtime/manifest.json', '{}')
        data = archive.read_bytes()
        part = 'runtime.zip.part000'
        (self.source/part).write_bytes(data)
        (self.source/'manifest.json').write_text(json.dumps(dict(format=1, parts=[
            dict(name=part, size=len(data), sha256=hashlib.sha256(data).hexdigest())])))

    def extract(self, command, **kwargs):
        with zipfile.ZipFile(command[3]) as zipped:
            zipped.extractall(command[4])

    def test_clean_restore_verifies_before_publishing(self):
        def verify(path):
            self.assertTrue((path/'manifest.json').is_file())
            self.assertFalse(self.destination.exists())
        with patch.object(seed, 'verify', side_effect=verify), \
                patch.object(seed.subprocess, 'run', side_effect=self.extract):
            seed.restore(self.source, self.destination)
        self.assertTrue((self.destination/'manifest.json').is_file())

    def test_corrupt_part_is_rejected_before_extraction(self):
        (self.source/'runtime.zip.part000').write_bytes(b'broken')
        with patch.object(seed.subprocess, 'run') as command:
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                seed.restore(self.source, self.destination)
            command.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_verification_failure_does_not_publish_runtime(self):
        with patch.object(seed, 'verify', side_effect=ValueError('invalid signature')), \
                patch.object(seed.subprocess, 'run', side_effect=self.extract):
            with self.assertRaisesRegex(ValueError, 'invalid signature'):
                seed.restore(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob('.tablecraft-seed-*')), [])

    def test_existing_invalid_runtime_is_preserved(self):
        self.destination.mkdir()
        marker = self.destination/'keep'
        marker.write_text('original')
        with patch.object(seed, 'verify', side_effect=ValueError('invalid runtime')), \
                patch.object(seed.subprocess, 'run') as command:
            with self.assertRaisesRegex(ValueError, 'invalid runtime'):
                seed.restore(self.source, self.destination)
            command.assert_not_called()
        self.assertEqual(marker.read_text(), 'original')

    def test_valid_existing_runtime_needs_no_seed(self):
        self.destination.mkdir()
        shutil.rmtree(self.source)
        with patch.object(seed, 'verify') as verify:
            self.assertEqual(seed.restore(self.source, self.destination), self.destination)
            verify.assert_called_once_with(self.destination)

    def test_archive_rejects_path_traversal_and_external_links(self):
        archive = self.root/'unsafe.zip'
        for name in ('../outside', '/outside', 'runtime/../../outside'):
            with zipfile.ZipFile(archive, 'w') as zipped:
                zipped.writestr(name, 'bad')
            with self.assertRaisesRegex(ValueError, 'Unsafe runtime archive path'):
                seed.validate_archive(archive)
        with zipfile.ZipFile(archive, 'w') as zipped:
            entry = zipfile.ZipInfo('runtime/link')
            entry.create_system = 3
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            zipped.writestr(entry, '../../outside')
        with self.assertRaisesRegex(ValueError, 'Unsafe runtime archive link'):
            seed.validate_archive(archive)


if __name__ == '__main__':
    unittest.main()
