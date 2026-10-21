#!/usr/bin/env python3
"""Store and restore the verified runtime in Git-sized archive parts."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import shutil
import stat
import subprocess
import tempfile
import zipfile

from portable_runtime import ROOT, verify

PART_SIZE = 48 * 1024 * 1024


def seed_manifest(seed):
    data = json.loads((seed/'manifest.json').read_text())
    if data.get('format') != 1 or not isinstance(data.get('parts'), list) or not data['parts']:
        raise ValueError('Unsupported or empty runtime seed manifest')
    expected = {'manifest.json'}
    for index, part in enumerate(data['parts']):
        name = 'runtime.zip.part{:03d}'.format(index)
        if part.get('name') != name or not 0 < part.get('size', 0) <= PART_SIZE:
            raise ValueError('Invalid runtime seed part')
        path = seed/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing runtime seed part: '+name)
        if path.stat().st_size != part['size'] or hashlib.sha256(path.read_bytes()).hexdigest() != part['sha256']:
            raise ValueError('Runtime seed checksum mismatch: '+name)
        expected.add(name)
    if {path.name for path in seed.iterdir()} != expected:
        raise ValueError('Unexpected files in runtime seed')
    return data


def create(seed):
    seed = Path(seed)
    verify(ROOT/'runtime')
    if seed.exists() or seed.is_symlink():
        raise ValueError('Runtime seed already exists; move it aside before replacing it')
    seed.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.tablecraft-seed-', dir=seed.parent) as temp:
        temp = Path(temp)
        archive = temp/'runtime.zip'
        subprocess.run(['/usr/bin/ditto', '--norsrc', '-c', '-k', '--keepParent',
                        str(ROOT/'runtime'), str(archive)], check=True)
        stage = temp/'seed'
        stage.mkdir()
        parts = []
        with archive.open('rb') as handle:
            while True:
                chunk = handle.read(PART_SIZE)
                if not chunk:
                    break
                name = 'runtime.zip.part{:03d}'.format(len(parts))
                (stage/name).write_bytes(chunk)
                parts.append(dict(name=name, size=len(chunk), sha256=hashlib.sha256(chunk).hexdigest()))
        (stage/'manifest.json').write_text(json.dumps(dict(format=1, parts=parts), indent=2)+'\n')
        seed_manifest(stage)
        stage.rename(seed)
    return seed


def validate_archive(archive):
    """Reject paths and links that could escape the extraction directory."""
    with zipfile.ZipFile(archive) as zipped:
        for entry in zipped.infolist():
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or path.parts[0] != 'runtime' or '\\' in entry.filename):
                raise ValueError('Unsafe runtime archive path')
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode):
                target = zipped.read(entry).decode('utf-8')
                resolved = posixpath.normpath(posixpath.join(str(path.parent), target))
                if target.startswith('/') or '\\' in target or not resolved.startswith('runtime/'):
                    raise ValueError('Unsafe runtime archive link')
            elif stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('Unsupported runtime archive entry')


def restore(seed, destination):
    seed, destination = Path(seed), Path(destination)
    # An invalid existing runtime must never be silently replaced.
    if destination.exists() or destination.is_symlink():
        verify(destination)
        return destination
    data = seed_manifest(seed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.tablecraft-seed-', dir=destination.parent) as temp:
        temp = Path(temp)
        archive = temp/'runtime.zip'
        with archive.open('wb') as handle:
            for part in data['parts']:
                with (seed/part['name']).open('rb') as source:
                    shutil.copyfileobj(source, handle)
        validate_archive(archive)
        extracted = temp/'extracted'
        subprocess.run(['/usr/bin/ditto', '-x', '-k', str(archive), str(extracted)], check=True)
        verify(extracted/'runtime')
        # mkdir is an atomic reservation: never overwrite a concurrent restore.
        destination.mkdir()
        try:
            for path in (extracted/'runtime').iterdir():
                path.rename(destination/path.name)
        except BaseException:
            shutil.rmtree(destination)
            raise
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('create', 'restore', 'check'))
    parser.add_argument('--seed', type=Path, default=ROOT/'runtime-seed')
    parser.add_argument('--runtime', type=Path, default=ROOT/'runtime')
    args = parser.parse_args()
    try:
        if args.action == 'create':
            if args.runtime != ROOT/'runtime':
                parser.error('create uses the runtime embedded in this project')
            print(create(args.seed))
        elif args.action == 'restore':
            print(restore(args.seed, args.runtime))
        else:
            seed_manifest(args.seed)
            print('Runtime seed checksums verified.')
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        parser.exit(1, 'Runtime seed: {}\n'.format(error))


if __name__ == '__main__':
    main()
