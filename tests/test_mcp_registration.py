"""Check guarded settings edits and prevent partial writes or truncated Swift strings."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import patch_mcp_registration as settings


class MCPRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='tablecraft-mcp-settings-')
        self.addCleanup(self.temp.cleanup)
        self.bundle=Path(self.temp.name)/'Fixture.app'
        (self.bundle/'Contents/MacOS').mkdir(parents=True)
        self.binary=self.bundle/'Contents/MacOS/TablePlus'
        self.mapping={(arch,address):64+i*320 for i,(arch,address,_,_) in enumerate(settings.edits())}
        raw=bytearray(b'X'*10000)
        for arch,address,before,_ in settings.edits():
            offset=self.mapping[arch,address];raw[offset:offset+len(before)]=before
        self.original=bytes(raw);self.binary.write_bytes(raw)
        mapping=self.mapping
        class FixtureMachO:
            def __init__(self,path,arch='arm64'):self.path,self.arch,self.base=Path(path),arch,0
            def offset(self,address):return mapping[self.arch,address]
            def read(self,address,size):
                offset=self.offset(address);return self.path.read_bytes()[offset:offset+size]
        self.addCleanup(patch.stopall)
        patch.object(settings,'MachO',FixtureMachO).start()
        patch.object(settings,'SOURCE_SHA256',hashlib.sha256(raw).hexdigest()).start()

    def test_changes_only_planned_bytes_and_preserves_length(self):
        settings.patch(self.bundle)
        expected=bytearray(self.original)
        for arch,address,before,after in settings.edits():
            offset=self.mapping[arch,address];expected[offset:offset+len(before)]=after
        self.assertEqual(self.binary.read_bytes(),expected)
        self.assertEqual(len(self.original),len(expected))
        self.assertEqual(settings.state(self.bundle),'TableCraft')
        self.assertEqual(settings.patch(self.bundle),[])

    def test_unknown_hash_is_rejected_without_writing(self):
        raw=self.original[:-1]+b'Y';self.binary.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'SHA-256'):settings.patch(self.bundle)
        self.assertEqual(self.binary.read_bytes(),raw)

    def test_partial_branding_is_rejected_without_writing(self):
        raw=bytearray(self.original)
        arch,address,_,after=settings.edits()[0];offset=self.mapping[arch,address]
        raw[offset:offset+len(after)]=after;self.binary.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'Incomplete'):settings.patch(self.bundle)
        self.assertEqual(self.binary.read_bytes(),raw)


if __name__=='__main__':unittest.main()
